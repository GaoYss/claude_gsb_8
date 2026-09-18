"""占绿审批与恢复核验接口。"""

from flask import Blueprint, request

from ..schemas import (
    occupation_filters,
    validate_occupation,
    validate_occupation_approval,
    validate_occupation_restore,
    validate_occupation_verify,
)
from ..services import OccupationService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("occupations", __name__)


@bp.get("/occupations")
def list_occupations():
    filters = occupation_filters(request.args)
    page, page_size = parse_page_args()
    query = OccupationService.list_occupations(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = OccupationService.summary(filters)
    return ok(data)


@bp.get("/occupations/summary")
def occupation_summary():
    return ok(OccupationService.summary(occupation_filters(request.args)))


@bp.post("/occupations")
def create_occupation():
    payload = validate_occupation(json_body())
    occupation = OccupationService.create(payload)
    return created(occupation.to_dict(detail=True), message="占绿申请登记成功，等待审批")


@bp.get("/occupations/<int:occupation_id>")
def get_occupation(occupation_id):
    return ok(OccupationService.detail(occupation_id))


@bp.put("/occupations/<int:occupation_id>")
def update_occupation(occupation_id):
    payload = validate_occupation(json_body())
    occupation = OccupationService.update(occupation_id, payload)
    return ok(occupation.to_dict(detail=True), message="占绿申请已更新")


@bp.patch("/occupations/<int:occupation_id>/approval")
def review_occupation(occupation_id):
    """审批：通过（标记占绿）或驳回。"""

    payload = validate_occupation_approval(json_body())
    occupation = OccupationService.approve(occupation_id, payload)
    message = "审批已通过，绿地已标记为占绿状态" if payload["action"] == "approved" else "占绿申请已驳回"
    return ok(occupation.to_dict(detail=True), message=message)


@bp.patch("/occupations/<int:occupation_id>/restore")
def restore_occupation(occupation_id):
    """恢复完成报备：录入实际恢复面积与苗木恢复情况，进入待核验。"""

    payload = validate_occupation_restore(json_body())
    occupation = OccupationService.report_restore(occupation_id, payload)
    return ok(occupation.to_dict(detail=True), message="恢复完成已报备，等待恢复核验")


@bp.patch("/occupations/<int:occupation_id>/verify")
def verify_occupation(occupation_id):
    """恢复核验：核对恢复面积与苗木恢复情况，通过后解除占绿状态。"""

    payload = validate_occupation_verify(json_body())
    occupation = OccupationService.verify(occupation_id, payload)
    return ok(occupation.to_dict(detail=True), message="恢复核验通过，绿地已解除占绿状态并恢复养护考核")


@bp.delete("/occupations/<int:occupation_id>")
def delete_occupation(occupation_id):
    OccupationService.delete(occupation_id)
    return ok(None, message="占绿申请已删除")
