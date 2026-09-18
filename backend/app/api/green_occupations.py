"""绿地占用登记接口。"""

from flask import Blueprint, request

from ..schemas import (
    validate_green_occupation,
    validate_occupation_approval,
    validate_occupation_verification,
)
from ..schemas.filters import occupation_filters
from ..services import GreenOccupationService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("green_occupations", __name__)


@bp.get("/green-occupations")
def list_occupations():
    filters = occupation_filters(request.args)
    page, page_size = parse_page_args()
    query = GreenOccupationService.list_occupations(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = GreenOccupationService.summary(filters)
    return ok(data)


@bp.get("/green-occupations/summary")
def occupation_summary():
    return ok(GreenOccupationService.summary(occupation_filters(request.args)))


@bp.post("/green-occupations")
def create_occupation():
    payload = validate_green_occupation(json_body())
    occupation = GreenOccupationService.create(payload)
    return created(occupation.to_dict(detail=True), message="绿地占用登记成功，待审批")


@bp.get("/green-occupations/<int:occupation_id>")
def get_occupation(occupation_id):
    return ok(GreenOccupationService.detail(occupation_id))


@bp.put("/green-occupations/<int:occupation_id>")
def update_occupation(occupation_id):
    payload = validate_green_occupation(json_body())
    occupation = GreenOccupationService.update(occupation_id, payload)
    return ok(occupation.to_dict(detail=True), message="绿地占用登记已更新")


@bp.patch("/green-occupations/<int:occupation_id>/approval")
def approve_occupation(occupation_id):
    """占用审批：批准后绿地标记为占绿状态，驳回则申请终止。"""

    payload = validate_occupation_approval(json_body())
    occupation = GreenOccupationService.approve(occupation_id, payload)
    message = "占用申请已批准，绿地已标记为占绿状态" if occupation.status == "approved" else "占用申请已驳回"
    return ok(occupation.to_dict(detail=True), message=message)


@bp.patch("/green-occupations/<int:occupation_id>/verification")
def verify_occupation(occupation_id):
    """恢复核验：核验恢复面积与苗木恢复情况，合格后绿地恢复正常养护。"""

    payload = validate_occupation_verification(json_body())
    occupation = GreenOccupationService.verify(occupation_id, payload)
    message = (
        "恢复核验合格，绿地已恢复正常养护"
        if occupation.status == "completed"
        else "恢复核验不合格，请整改后重新核验"
    )
    return ok(occupation.to_dict(detail=True), message=message)


@bp.delete("/green-occupations/<int:occupation_id>")
def delete_occupation(occupation_id):
    GreenOccupationService.delete(occupation_id)
    return ok(None, message="绿地占用登记已删除")
