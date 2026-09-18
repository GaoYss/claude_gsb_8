"""占绿审批与恢复核验业务逻辑。

状态流转：

    pending（待审批）
        ── 审批通过 ──> approved（占绿中）── 报备恢复完成 ──> restored（待核验）
        │                                                ── 核验通过 ──> verified（核验通过）
        └── 驳回 ─────> rejected（已驳回）

规则要点：

1. 审批通过即在对应绿地上标记占绿状态，同一绿地同一时间只允许一条生效中的占绿记录；
2. 占绿期间（含待核验）绿地不参与养护考核：不计逾期、不进养护考核排名，看板单独统计；
3. 恢复完成需报备实际恢复面积与苗木恢复情况，核验时恢复面积不得少于审批占用面积，
   且必须登记苗木恢复情况，核验通过后绿地才解除占绿状态、重新纳入养护考核；
4. 生效中与已核验的记录为审批/核验履历，不允许删除。
"""

from decimal import Decimal

from sqlalchemy import func, or_

from ..constants import ENUM_GROUPS
from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import GreenSpace, Occupation
from ..models.occupation import ACTIVE_STATUSES
from ..models.mixins import utcnow
from ..utils.dates import today
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix


class OccupationService(BaseService):
    """占绿审批：登记、审批、恢复报备与恢复核验。"""

    model = Occupation
    label = "占绿审批"
    code_field = "occupation_no"
    code_width = 3

    SORTABLE = {
        "apply_date": Occupation.apply_date,
        "start_date": Occupation.start_date,
        "end_date": Occupation.end_date,
        "occupy_area_sqm": Occupation.occupy_area_sqm,
        "created_at": Occupation.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("OC")

    # ------------------------------------------------------------ 校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "所选绿地不存在"})
        if space.status == "archived":
            raise ConflictError(f"绿地「{space.name}」已归档，不能再申请占用")

        start_date = payload.get("start_date", instance.start_date)
        end_date = payload.get("end_date", instance.end_date)
        apply_date = payload.get("apply_date", instance.apply_date)
        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                "登记失败", details={"end_date": "占用结束日期不能早于开始日期"}
            )
        if apply_date and start_date and apply_date > start_date:
            raise ValidationError(
                "登记失败", details={"start_date": "占用开始日期不能早于申请日期"}
            )
        if start_date and space.established_date and start_date < space.established_date:
            raise ValidationError(
                "登记失败",
                details={"start_date": f"占用开始日期不能早于该绿地建成日期 {space.established_date}"},
            )

        occupy_area = payload.get("occupy_area_sqm", instance.occupy_area_sqm)
        if occupy_area is not None and Decimal(str(occupy_area)) > Decimal(str(space.area_sqm or 0)):
            raise ValidationError(
                "登记失败",
                details={"occupy_area_sqm": f"占用面积不能超过绿地总面积 {to_float(space.area_sqm)} ㎡"},
            )

    @classmethod
    def prepare_update(cls, instance, payload):
        if instance.status != "pending":
            raise ConflictError("仅待审批的占绿申请可以修改，审批后请走恢复核验流程")
        cls.prepare_instance(instance, payload)

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(Occupation.green_space_id == filters["green_space_id"])
        if filters.get("status"):
            query = query.filter(Occupation.status == filters["status"])
        if filters.get("reason"):
            query = query.filter(Occupation.reason == filters["reason"])
        if filters.get("date_from"):
            query = query.filter(Occupation.start_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(Occupation.start_date <= filters["date_to"])
        if filters.get("active_only"):
            query = query.filter(Occupation.status.in_(ACTIVE_STATUSES))
        if filters.get("overdue_restore"):
            query = query.filter(
                Occupation.status == "approved", Occupation.end_date < today()
            )
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Occupation.occupation_no.like(like),
                    Occupation.purpose.like(like),
                    Occupation.applicant.like(like),
                    Occupation.scope_description.like(like),
                )
            )
        return query

    @classmethod
    def list_occupations(cls, filters, args):
        query = cls._apply_filters(db.session.query(Occupation), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, Occupation.apply_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def summary(cls, filters):
        """占绿汇总：按状态统计条数与占用面积，并提示逾期未恢复数量。"""

        rows = (
            cls._apply_filters(
                db.session.query(
                    Occupation.status,
                    func.count(Occupation.id),
                    func.coalesce(func.sum(Occupation.occupy_area_sqm), 0),
                ),
                filters,
            )
            .group_by(Occupation.status)
            .all()
        )
        by_status = {code: {"count": 0, "area_sqm": 0.0} for code in ENUM_GROUPS["occupation_status"].values}
        for status, count, area in rows:
            by_status[status] = {"count": count, "area_sqm": to_float(area) or 0}

        overdue_restore = (
            db.session.query(func.count(Occupation.id))
            .filter(Occupation.status == "approved", Occupation.end_date < today())
            .scalar()
            or 0
        )
        active_area = (
            db.session.query(func.coalesce(func.sum(Occupation.occupy_area_sqm), 0))
            .filter(Occupation.status.in_(ACTIVE_STATUSES))
            .scalar()
        )
        return {
            "total_count": sum(item["count"] for item in by_status.values()),
            "by_status": by_status,
            "active_count": sum(by_status[code]["count"] for code in ACTIVE_STATUSES),
            "active_area_sqm": to_float(active_area) or 0,
            "overdue_restore_count": overdue_restore,
        }

    # ------------------------------------------------------------ 审批
    @classmethod
    def approve(cls, obj_id, payload):
        occupation = cls.get(obj_id)
        if occupation.status != "pending":
            raise ConflictError(
                f"当前状态为「{ENUM_GROUPS['occupation_status'].label(occupation.status)}」，不能再审批"
            )
        action = payload["action"]
        if action not in ("approved", "rejected"):
            raise ValidationError("审批失败", details={"action": "审批结论只能是 approved（通过）或 rejected（驳回）"})

        if action == "approved":
            # 同一绿地同一时间只允许一条生效中的占绿记录
            overlap = (
                db.session.query(Occupation)
                .filter(
                    Occupation.green_space_id == occupation.green_space_id,
                    Occupation.status.in_(ACTIVE_STATUSES),
                    Occupation.id != occupation.id,
                )
                .first()
            )
            if overlap is not None:
                raise ConflictError(
                    f"该绿地已有生效中的占绿记录 {overlap.occupation_no}，"
                    "完成恢复核验后才能审批新的占用申请"
                )

        occupation.approved_by = payload["approved_by"]
        occupation.approval_remark = payload.get("approval_remark")
        occupation.approved_at = utcnow()
        occupation.status = action
        db.session.commit()
        return occupation

    # ------------------------------------------------------------ 恢复报备与核验
    @classmethod
    def report_restore(cls, obj_id, payload):
        """恢复完成报备：占绿中 -> 待核验，等待管理人员现场核验。"""

        occupation = cls.get(obj_id)
        if occupation.status not in ("approved", "restored"):
            raise ConflictError(
                f"当前状态为「{ENUM_GROUPS['occupation_status'].label(occupation.status)}」，"
                "仅占绿中的记录可以报备恢复完成"
            )
        restored_area = payload["restored_area_sqm"]
        if Decimal(str(restored_area)) > Decimal(str(occupation.green_space.area_sqm or 0)):
            raise ValidationError(
                "恢复报备失败",
                details={"restored_area_sqm": "实际恢复面积不能超过绿地总面积"},
            )
        occupation.restored_date = payload["restored_date"]
        occupation.restored_area_sqm = restored_area
        occupation.restored_plants = payload["restored_plants"]
        occupation.restore_remark = payload.get("restore_remark")
        occupation.status = "restored"
        db.session.commit()
        return occupation

    @classmethod
    def verify(cls, obj_id, payload):
        """恢复核验：核对恢复面积与苗木恢复情况，通过后解除占绿状态。"""

        occupation = cls.get(obj_id)
        if occupation.status != "restored":
            raise ConflictError(
                f"当前状态为「{ENUM_GROUPS['occupation_status'].label(occupation.status)}」，"
                "仅待核验的记录可以核验"
            )

        problems = {}
        restored_area = Decimal(str(occupation.restored_area_sqm or 0))
        occupied_area = Decimal(str(occupation.occupy_area_sqm or 0))
        if restored_area < occupied_area:
            gap = (occupied_area - restored_area).quantize(Decimal("0.01"))
            problems["restored_area_sqm"] = (
                f"实际恢复面积 {restored_area} ㎡ 少于审批占用面积 {occupied_area} ㎡，差额 {gap} ㎡，核验不通过"
            )
        if not (occupation.restored_plants or "").strip():
            problems["restored_plants"] = "未登记苗木恢复情况，无法核验"

        if problems:
            raise ConflictError("恢复核验未通过，请按要求整改后重新报备恢复", details=problems)

        occupation.verified_by = payload["verified_by"]
        occupation.verify_remark = payload.get("verify_remark")
        occupation.verified_at = utcnow()
        occupation.status = "verified"
        db.session.commit()
        return occupation

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id):
        occupation = cls.get(obj_id)
        if occupation.status in ACTIVE_STATUSES:
            raise ConflictError("占绿生效中，不能删除；请完成恢复核验后再操作")
        if occupation.status == "verified":
            raise ConflictError("核验通过的占绿记录属审批履历，不能删除")
        db.session.delete(occupation)
        db.session.commit()
        return occupation

    @classmethod
    def status_summary(cls):
        rows = (
            db.session.query(Occupation.status, func.count(Occupation.id))
            .group_by(Occupation.status)
            .all()
        )
        summary = {code: 0 for code in ENUM_GROUPS["occupation_status"].values}
        for status, count in rows:
            summary[status] = count
        return summary

    # ------------------------------------------------------------ 养护考核口径
    @staticmethod
    def occupied_space_ids(on_date=None):
        """指定日期处于占绿状态的绿地 id 集合，供养护考核统计排除使用。

        - 已审批且到达占用开始日期（占用到期未恢复仍视为占绿中）；
        - 已报备恢复但尚未核验通过（待核验期间继续豁免）。
        """

        on_date = on_date or today()
        rows = (
            db.session.query(Occupation.green_space_id)
            .filter(
                or_(
                    db.and_(Occupation.status == "approved", Occupation.start_date <= on_date),
                    Occupation.status == "restored",
                )
            )
            .all()
        )
        return {row[0] for row in rows}
