"""绿地占用登记业务逻辑。

业务流程：登记（待审批）→ 审批（占绿中 / 已驳回）→ 恢复核验（已恢复）。
审批通过后绿地台账标记为「占绿中」，占绿期间不参与养护考核；
恢复核验合格后绿地还原为占用前状态，核验不合格则保持占绿并记录核验结果。
"""

from datetime import timedelta

from sqlalchemy import func, or_

from ..constants import ENUM_GROUPS
from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import GreenSpace, GreenSpaceOccupation
from ..models.mixins import utcnow
from ..utils.dates import today
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix

# 占用到期前多少天视为「即将到期」
EXPIRING_SOON_DAYS = 14


class GreenOccupationService(BaseService):
    """绿地占用登记：申请、审批、占绿状态联动与恢复核验。"""

    model = GreenSpaceOccupation
    label = "绿地占用登记"
    code_field = "occupation_no"
    code_width = 3

    SORTABLE = {
        "start_date": GreenSpaceOccupation.start_date,
        "end_date": GreenSpaceOccupation.end_date,
        "area_sqm": GreenSpaceOccupation.area_sqm,
        "created_at": GreenSpaceOccupation.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("GO")

    # ------------------------------------------------------------ 校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "所选绿地不存在"})
        if space.status == "archived":
            raise ConflictError(f"绿地「{space.name}」已归档，不能登记占用")

        start_date = payload.get("start_date", instance.start_date)
        end_date = payload.get("end_date", instance.end_date)
        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                "登记失败", details={"end_date": "计划恢复日期不能早于占用开始日期"}
            )

        area_sqm = payload.get("area_sqm", instance.area_sqm)
        if area_sqm is not None and space.area_sqm is not None:
            if float(area_sqm) > float(space.area_sqm):
                raise ValidationError(
                    "登记失败",
                    details={
                        "area_sqm": f"占用面积不能超过绿地总面积 {to_float(space.area_sqm)} ㎡"
                    },
                )

    @classmethod
    def prepare_update(cls, instance, payload):
        if instance.status != "pending":
            raise ConflictError("占用登记已审批，登记内容不能再修改")
        cls.prepare_instance(instance, payload)

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(
                GreenSpaceOccupation.green_space_id == filters["green_space_id"]
            )
        if filters.get("status"):
            query = query.filter(GreenSpaceOccupation.status == filters["status"])
        if filters.get("category"):
            query = query.filter(GreenSpaceOccupation.category == filters["category"])
        if filters.get("date_from"):
            query = query.filter(GreenSpaceOccupation.start_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(GreenSpaceOccupation.start_date <= filters["date_to"])
        if filters.get("expired"):
            query = query.filter(
                GreenSpaceOccupation.status == "approved",
                GreenSpaceOccupation.end_date < today(),
            )
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    GreenSpaceOccupation.occupation_no.like(like),
                    GreenSpaceOccupation.applicant.like(like),
                    GreenSpaceOccupation.reason.like(like),
                    GreenSpaceOccupation.location_desc.like(like),
                )
            )
        return query

    @classmethod
    def list_occupations(cls, filters, args):
        query = cls._apply_filters(db.session.query(GreenSpaceOccupation), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, GreenSpaceOccupation.created_at.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def summary(cls, filters):
        """占用汇总：状态分布、占绿面积与超期/临期提醒。"""

        status_rows = (
            cls._apply_filters(
                db.session.query(
                    GreenSpaceOccupation.status, func.count(GreenSpaceOccupation.id)
                ),
                filters,
            )
            .group_by(GreenSpaceOccupation.status)
            .all()
        )
        by_status = {code: 0 for code in ENUM_GROUPS["occupation_status"].values}
        for status, count in status_rows:
            by_status[status] = count

        occupied_area = cls._apply_filters(
            db.session.query(func.coalesce(func.sum(GreenSpaceOccupation.area_sqm), 0)),
            {**filters, "status": "approved"},
        ).scalar()

        current = today()
        expired_count = cls._apply_filters(
            db.session.query(func.count(GreenSpaceOccupation.id)),
            {**filters, "expired": True},
        ).scalar() or 0
        expiring_soon = cls._apply_filters(
            db.session.query(func.count(GreenSpaceOccupation.id)).filter(
                GreenSpaceOccupation.status == "approved",
                GreenSpaceOccupation.end_date >= current,
                GreenSpaceOccupation.end_date <= current + timedelta(days=EXPIRING_SOON_DAYS),
            ),
            filters,
        ).scalar() or 0

        return {
            "total_count": sum(by_status.values()),
            "by_status": by_status,
            "occupied_area": to_float(occupied_area) or 0,
            "expired_count": expired_count,
            "expiring_soon_count": expiring_soon,
        }

    # ------------------------------------------------------------ 审批
    @classmethod
    def approve(cls, obj_id, payload):
        """审批占用申请。

        批准：绿地台账标记为「占绿中」（占用前状态留档，恢复时还原）；
        驳回：仅记录审批信息，绿地状态不受影响。
        """

        occupation = cls.get(obj_id)
        if occupation.status != "pending":
            status_label = ENUM_GROUPS["occupation_status"].label(occupation.status)
            raise ConflictError(f"该占用登记已审批（{status_label}），不能重复审批")

        result = payload["result"]
        occupation.approved_by = payload["approved_by"]
        occupation.approved_at = utcnow()
        occupation.approval_comment = payload.get("approval_comment")

        if result == "rejected":
            occupation.status = "rejected"
            db.session.commit()
            return occupation

        space = occupation.green_space
        if space.status == "archived":
            raise ConflictError(f"绿地「{space.name}」已归档，不能批准占用")
        active = (
            db.session.query(func.count(GreenSpaceOccupation.id))
            .filter(
                GreenSpaceOccupation.green_space_id == space.id,
                GreenSpaceOccupation.status == "approved",
                GreenSpaceOccupation.id != occupation.id,
            )
            .scalar()
            or 0
        )
        if active:
            raise ConflictError(f"绿地「{space.name}」已存在生效中的占用登记，不能重复批准")

        occupation.status = "approved"
        occupation.space_status_before = space.status
        space.status = "occupied"
        db.session.commit()
        return occupation

    # ------------------------------------------------------------ 恢复核验
    @classmethod
    def verify(cls, obj_id, payload):
        """恢复核验：核验恢复面积与苗木恢复情况。

        合格：占用结束，绿地还原为占用前状态；
        不合格：保持占绿状态，记录本次核验结论，整改后可再次核验。
        """

        occupation = cls.get(obj_id)
        if occupation.status != "approved":
            raise ConflictError("只有占绿中的占用登记才能进行恢复核验")

        occupation.restored_area_sqm = payload["restored_area_sqm"]
        occupation.plant_restoration = payload["plant_restoration"]
        occupation.verify_result = payload["verify_result"]
        occupation.verified_by = payload["verified_by"]
        occupation.verified_at = utcnow()
        occupation.verify_comment = payload.get("verify_comment")

        if payload["verify_result"] == "qualified":
            occupation.status = "completed"
            space = occupation.green_space
            if space.status == "occupied":
                space.status = occupation.space_status_before or "normal"
        db.session.commit()
        return occupation

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id):
        occupation = cls.get(obj_id)
        if occupation.status == "approved":
            raise ConflictError("该占用正在生效（占绿中），请先完成恢复核验后再删除")
        db.session.delete(occupation)
        db.session.commit()
        return occupation
