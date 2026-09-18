"""占绿审批与恢复核验模型。"""

from ..constants import OCCUPATION_REASON, OCCUPATION_STATUS
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column

# 占绿生效中的状态：审批通过后到核验通过前，绿地均处于占绿状态
ACTIVE_STATUSES = ("approved", "restored")
# 终态：已驳回、核验通过后不再参与状态流转
FINAL_STATUSES = ("rejected", "verified")


class Occupation(TimestampMixin, db.Model):
    """占用绿地审批：登记事由、范围、期限与恢复要求，审批后标记占绿，恢复后核验。"""

    __tablename__ = "green_space_occupation"

    id = db.Column(db.Integer, primary_key=True)
    occupation_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason = db.Column(db.String(32), nullable=False, index=True)
    purpose = db.Column(db.String(255), nullable=False)
    scope_description = db.Column(db.Text)
    occupy_area_sqm = db.Column(quantity_column(), nullable=False, default=0)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    applicant = db.Column(db.String(96))
    applicant_phone = db.Column(db.String(32))
    apply_date = db.Column(db.Date, nullable=False, index=True)
    restore_requirement = db.Column(db.Text)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)

    # 审批信息
    approved_by = db.Column(db.String(64))
    approved_at = db.Column(db.DateTime)
    approval_remark = db.Column(db.Text)

    # 恢复完成报备
    restored_date = db.Column(db.Date)
    restored_area_sqm = db.Column(quantity_column())
    restored_plants = db.Column(db.Text)
    restore_remark = db.Column(db.Text)

    # 恢复核验
    verified_by = db.Column(db.String(64))
    verified_at = db.Column(db.DateTime)
    verify_remark = db.Column(db.Text)

    green_space = db.relationship("GreenSpace", back_populates="occupations", lazy="joined")

    @property
    def is_active(self):
        """占绿生效中（含待核验）：期间绿地不参与养护考核。"""

        return self.status in ACTIVE_STATUSES

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "occupation_no": self.occupation_no,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "reason": self.reason,
            "reason_label": OCCUPATION_REASON.label(self.reason),
            "purpose": self.purpose,
            "scope_description": self.scope_description,
            "occupy_area_sqm": to_float(self.occupy_area_sqm),
            "start_date": format_date(self.start_date),
            "end_date": format_date(self.end_date),
            "applicant": self.applicant,
            "applicant_phone": self.applicant_phone,
            "apply_date": format_date(self.apply_date),
            "status": self.status,
            "status_label": OCCUPATION_STATUS.label(self.status),
            "is_active": self.is_active,
            "approved_by": self.approved_by,
            "approved_at": format_datetime(self.approved_at),
            "restored_date": format_date(self.restored_date),
            "restored_area_sqm": to_float(self.restored_area_sqm),
            "verified_by": self.verified_by,
            "verified_at": format_datetime(self.verified_at),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["restore_requirement"] = self.restore_requirement
            data["approval_remark"] = self.approval_remark
            data["restored_plants"] = self.restored_plants
            data["restore_remark"] = self.restore_remark
            data["verify_remark"] = self.verify_remark
        return data
