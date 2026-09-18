"""占绿审批与恢复核验校验规则。"""

from ..constants import OCCUPATION_REASON, OCCUPATION_STATUS
from .common import PHONE_PATTERN, PayloadValidator


def validate_occupation(payload):
    """登记占用事由、范围、期限与恢复要求（创建/编辑草稿）。"""

    validator = (
        PayloadValidator(payload)
        .string("occupation_no", "占绿编号", max_length=32)
        .integer("green_space_id", "所属绿地", required=True, min_value=1)
        .enum("reason", "占用事由", group=OCCUPATION_REASON, required=True)
        .string("purpose", "占用事由说明", required=True, max_length=255)
        .text("scope_description", "占用范围描述", max_length=2000)
        .number("occupy_area_sqm", "占用面积（㎡）", required=True, min_value=0.01, max_value=99999999)
        .date("start_date", "占用开始日期", required=True)
        .date("end_date", "占用结束日期", required=True)
        .string("applicant", "申请单位/申请人", max_length=96)
        .string("applicant_phone", "联系电话", max_length=32, pattern=PHONE_PATTERN,
                pattern_message="联系电话格式不正确")
        .date("apply_date", "申请日期", required=True)
        .text("restore_requirement", "恢复要求", max_length=2000)
    )
    validator.check(
        lambda: validator.clean.get("end_date") and validator.clean.get("start_date")
        and validator.clean["end_date"] < validator.clean["start_date"],
        "end_date", "占用结束日期不能早于开始日期",
    )
    validator.check(
        lambda: validator.clean.get("apply_date") and validator.clean.get("start_date")
        and validator.clean["apply_date"] > validator.clean["start_date"],
        "start_date", "占用开始日期不能早于申请日期",
    )
    return validator.done()


def validate_occupation_approval(payload):
    """审批：通过或驳回，并记录审批人与意见。"""

    return (
        PayloadValidator(payload)
        .string("action", "审批结论", required=True, max_length=16)
        .string("approved_by", "审批人", required=True, max_length=64)
        .text("approval_remark", "审批意见", max_length=2000)
        .done()
    )


def validate_occupation_restore(payload):
    """恢复完成报备：实际恢复面积、苗木恢复情况与说明。"""

    return (
        PayloadValidator(payload)
        .date("restored_date", "恢复完成日期", required=True)
        .number("restored_area_sqm", "实际恢复面积（㎡）", required=True,
                min_value=0.01, max_value=99999999)
        .text("restored_plants", "苗木恢复情况", required=True, max_length=2000)
        .text("restore_remark", "恢复说明", max_length=2000)
        .done()
    )


def validate_occupation_verify(payload):
    """恢复核验：登记核验人、核验意见。核验口径由后端统一校验面积与苗木。"""

    return (
        PayloadValidator(payload)
        .string("verified_by", "核验人", required=True, max_length=64)
        .text("verify_remark", "核验意见", max_length=2000)
        .done()
    )
