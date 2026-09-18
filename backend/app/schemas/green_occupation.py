"""绿地占用登记校验规则。"""

from ..constants import APPROVAL_RESULT, OCCUPATION_CATEGORY, VERIFY_RESULT
from .common import PayloadValidator


def validate_green_occupation(payload):
    return (
        PayloadValidator(payload)
        .string("occupation_no", "占用编号", max_length=32)
        .integer("green_space_id", "占用绿地", required=True, min_value=1)
        .string("applicant", "申请单位/人", required=True, max_length=96)
        .string("contact_phone", "联系电话", max_length=32)
        .enum("category", "占用类型", group=OCCUPATION_CATEGORY, default="construction")
        .string("reason", "占用事由", required=True, max_length=255)
        .string("location_desc", "占用范围说明", max_length=255)
        .number("area_sqm", "占用面积", required=True, min_value=0.01, max_value=99999999)
        .date("start_date", "占用开始日期", required=True)
        .date("end_date", "计划恢复日期", required=True)
        .text("restoration_requirement", "恢复要求", required=True, max_length=2000)
        .string("operator", "登记人", max_length=64)
        .text("remark", "备注", max_length=2000)
        .done()
    )


def validate_occupation_approval(payload):
    """占用审批：通过或驳回，需填写审批人与审批意见。"""

    return (
        PayloadValidator(payload)
        .enum("result", "审批结论", group=APPROVAL_RESULT, required=True)
        .string("approved_by", "审批人", required=True, max_length=64)
        .string("approval_comment", "审批意见", max_length=500)
        .done()
    )


def validate_occupation_verification(payload):
    """恢复核验：核验面积、苗木恢复情况与核验结论。"""

    return (
        PayloadValidator(payload)
        .enum("verify_result", "核验结论", group=VERIFY_RESULT, required=True)
        .number("restored_area_sqm", "恢复面积", required=True, min_value=0, max_value=99999999)
        .text("plant_restoration", "苗木恢复情况", required=True, max_length=2000)
        .string("verified_by", "核验人", required=True, max_length=64)
        .string("verify_comment", "核验意见", max_length=500)
        .done()
    )
