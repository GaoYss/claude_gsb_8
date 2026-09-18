"""绿地占用登记模型。"""

from ..constants import OCCUPATION_CATEGORY, OCCUPATION_STATUS, VERIFY_RESULT
from ..extensions import db
from ..utils.dates import format_date, format_datetime, today
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class GreenSpaceOccupation(TimestampMixin, db.Model):
    """绿地占用登记：占用申请、审批、占绿期间管理与恢复核验全过程留痕。"""

    __tablename__ = "green_space_occupation"

    id = db.Column(db.Integer, primary_key=True)
    occupation_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    applicant = db.Column(db.String(96), nullable=False)
    contact_phone = db.Column(db.String(32))
    category = db.Column(db.String(32), nullable=False, default="construction", index=True)
    reason = db.Column(db.String(255), nullable=False)
    location_desc = db.Column(db.String(255))
    area_sqm = db.Column(quantity_column(), nullable=False, default=0)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False)
    restoration_requirement = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)

    # 审批信息（通过或驳回时写入）
    approved_by = db.Column(db.String(64))
    approved_at = db.Column(db.DateTime)
    approval_comment = db.Column(db.String(500))
    # 审批通过前的绿地状态，恢复核验合格后还原
    space_status_before = db.Column(db.String(16))

    # 恢复核验信息（每次核验刷新，记录最近一次的核验结论）
    restored_area_sqm = db.Column(quantity_column())
    plant_restoration = db.Column(db.Text)
    verify_result = db.Column(db.String(16))
    verified_by = db.Column(db.String(64))
    verified_at = db.Column(db.DateTime)
    verify_comment = db.Column(db.String(500))

    operator = db.Column(db.String(64))
    remark = db.Column(db.Text)

    green_space = db.relationship("GreenSpace", back_populates="occupations", lazy="joined")

    @property
    def is_expired(self):
        """占绿中且已过占用期限即为超期占用。"""

        return self.status == "approved" and self.end_date < today()

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "occupation_no": self.occupation_no,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "applicant": self.applicant,
            "contact_phone": self.contact_phone,
            "category": self.category,
            "category_label": OCCUPATION_CATEGORY.label(self.category),
            "reason": self.reason,
            "location_desc": self.location_desc,
            "area_sqm": to_float(self.area_sqm),
            "start_date": format_date(self.start_date),
            "end_date": format_date(self.end_date),
            "status": self.status,
            "status_label": OCCUPATION_STATUS.label(self.status),
            "is_expired": self.is_expired,
            "approved_by": self.approved_by,
            "approved_at": format_datetime(self.approved_at),
            "approval_comment": self.approval_comment,
            "restored_area_sqm": to_float(self.restored_area_sqm),
            "verify_result": self.verify_result,
            "verify_result_label": (
                VERIFY_RESULT.label(self.verify_result) if self.verify_result else None
            ),
            "verified_by": self.verified_by,
            "verified_at": format_datetime(self.verified_at),
            "operator": self.operator,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["restoration_requirement"] = self.restoration_requirement
            data["plant_restoration"] = self.plant_restoration
            data["verify_comment"] = self.verify_comment
            data["space_status_before"] = self.space_status_before
            data["remark"] = self.remark
        return data
