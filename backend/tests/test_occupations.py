"""绿地占用登记测试：登记校验、审批、占绿状态联动、恢复核验与养护考核排除。"""

from datetime import date, timedelta


def _create_payload(space_id, **overrides):
    payload = {
        "green_space_id": space_id,
        "applicant": "某建设工程公司",
        "contact_phone": "0571-88000000",
        "category": "construction",
        "reason": "地铁施工临时占用绿化带",
        "location_desc": "路口东南侧绿化带",
        "area_sqm": 200,
        "start_date": "2026-03-01",
        "end_date": "2026-09-30",
        "restoration_requirement": "占用结束后恢复绿化带原貌，苗木成活率不低于 95%",
        "operator": "王海涛",
    }
    payload.update(overrides)
    return payload


def _approve(api, occupation_id, result="approved", **overrides):
    payload = {"result": result, "approved_by": "园林局审批处", "approval_comment": "同意占用"}
    payload.update(overrides)
    return api.patch(f"/api/v1/green-occupations/{occupation_id}/approval", payload)


def _verify(api, occupation_id, verify_result="qualified", **overrides):
    payload = {
        "verify_result": verify_result,
        "restored_area_sqm": 200,
        "plant_restoration": "已补植金森女贞色块 200 ㎡，长势良好",
        "verified_by": "沈建国",
        "verify_comment": "符合恢复要求",
    }
    payload.update(overrides)
    return api.patch(f"/api/v1/green-occupations/{occupation_id}/verification", payload)


def _space_status(api, space_id):
    return api.data(api.get(f"/api/v1/green-spaces/{space_id}"))["status"]


# ------------------------------------------------------------ 登记与校验
def test_create_occupation_generates_code_in_sequence(api, make_space):
    space = make_space()
    first = api.data(api.post("/api/v1/green-occupations", _create_payload(space.id)), 201)
    second = api.data(api.post("/api/v1/green-occupations", _create_payload(space.id)), 201)
    assert first["status"] == "pending"
    assert first["occupation_no"].startswith("GO-")
    assert first["occupation_no"].endswith("-001")
    assert second["occupation_no"].endswith("-002")


def test_create_occupation_validates_required_fields(api):
    response = api.post("/api/v1/green-occupations", {"category": "event"})
    assert response.status_code == 422
    details = response.get_json()["data"]
    for field in ("green_space_id", "applicant", "reason", "area_sqm",
                  "start_date", "end_date", "restoration_requirement"):
        assert field in details


def test_create_occupation_rejects_invalid_dates_and_area(api, make_space):
    space = make_space(area_sqm=100)
    response = api.post("/api/v1/green-occupations", _create_payload(
        space.id, start_date="2026-09-01", end_date="2026-03-01",
    ))
    assert response.status_code == 422
    assert "end_date" in response.get_json()["data"]

    response = api.post("/api/v1/green-occupations", _create_payload(space.id, area_sqm=120))
    assert response.status_code == 422
    assert "area_sqm" in response.get_json()["data"]


def test_create_occupation_rejects_missing_or_archived_space(api, make_space):
    response = api.post("/api/v1/green-occupations", _create_payload(9999))
    assert response.status_code == 422

    archived = make_space(status="archived")
    response = api.post("/api/v1/green-occupations", _create_payload(archived.id))
    assert response.status_code == 409


# ------------------------------------------------------------ 审批
def test_approve_marks_space_occupied(api, make_space, make_occupation):
    space = make_space()
    occupation = make_occupation(space=space)

    data = api.data(_approve(api, occupation.id))
    assert data["status"] == "approved"
    assert data["approved_by"] == "园林局审批处"
    assert data["approved_at"] is not None
    assert _space_status(api, space.id) == "occupied"


def test_approve_is_idempotent_safe_and_space_unique(api, make_space, make_occupation):
    space = make_space()
    first = make_occupation(space=space)
    second = make_occupation(space=space, reason="管线敷设临时占用")

    api.data(_approve(api, first.id))
    # 同一绿地已存在生效中的占用，第二笔不能批准
    response = _approve(api, second.id)
    assert response.status_code == 409
    # 已审批的不能重复审批
    assert _approve(api, first.id).status_code == 409


def test_reject_keeps_space_status(api, make_space, make_occupation):
    space = make_space()
    occupation = make_occupation(space=space)

    data = api.data(_approve(api, occupation.id, result="rejected",
                             approval_comment="樱花季期间不允许占用"))
    assert data["status"] == "rejected"
    assert data["approval_comment"] == "樱花季期间不允许占用"
    assert _space_status(api, space.id) == "normal"


def test_approve_fails_when_space_archived_after_registration(api, make_space, make_occupation):
    space = make_space()
    occupation = make_occupation(space=space)
    api.data(api.put(f"/api/v1/green-spaces/{space.id}", {
        "name": space.name,
        "district": space.district,
        "green_type": space.green_type,
        "maintenance_grade": space.maintenance_grade,
        "area_sqm": float(space.area_sqm),
        "status": "archived",
    }))

    assert _approve(api, occupation.id).status_code == 409


def test_approval_requires_valid_payload(api, make_occupation):
    occupation = make_occupation()
    response = _approve(api, occupation.id, result="unknown")
    assert response.status_code == 422
    response = api.patch(f"/api/v1/green-occupations/{occupation.id}/approval",
                         {"result": "approved"})
    assert response.status_code == 422


# ------------------------------------------------------------ 编辑与删除保护
def test_update_only_allowed_before_approval(api, make_occupation):
    occupation = make_occupation()
    data = api.data(api.put(f"/api/v1/green-occupations/{occupation.id}",
                            _create_payload(occupation.green_space_id, area_sqm=150)))
    assert data["area_sqm"] == 150.0

    api.data(_approve(api, occupation.id))
    response = api.put(f"/api/v1/green-occupations/{occupation.id}",
                       _create_payload(occupation.green_space_id, area_sqm=100))
    assert response.status_code == 409


def test_delete_rules_by_status(api, make_occupation):
    pending = make_occupation()
    assert api.delete(f"/api/v1/green-occupations/{pending.id}").status_code == 200

    rejected = make_occupation()
    api.data(_approve(api, rejected.id, result="rejected"))
    assert api.delete(f"/api/v1/green-occupations/{rejected.id}").status_code == 200

    approved = make_occupation()
    api.data(_approve(api, approved.id))
    assert api.delete(f"/api/v1/green-occupations/{approved.id}").status_code == 409

    completed = make_occupation()
    api.data(_approve(api, completed.id))
    api.data(_verify(api, completed.id))
    assert api.delete(f"/api/v1/green-occupations/{completed.id}").status_code == 200


# ------------------------------------------------------------ 恢复核验
def test_verify_qualified_restores_space_status(api, make_space, make_occupation):
    space = make_space()
    occupation = make_occupation(space=space)
    api.data(_approve(api, occupation.id))
    assert _space_status(api, space.id) == "occupied"

    data = api.data(_verify(api, occupation.id, restored_area_sqm=200))
    assert data["status"] == "completed"
    assert data["verify_result"] == "qualified"
    assert data["restored_area_sqm"] == 200.0
    assert data["verified_at"] is not None
    assert _space_status(api, space.id) == "normal"


def test_verify_restores_previous_space_status(api, make_space, make_occupation):
    space = make_space(status="repairing")
    occupation = make_occupation(space=space)
    api.data(_approve(api, occupation.id))
    assert _space_status(api, space.id) == "occupied"

    api.data(_verify(api, occupation.id))
    assert _space_status(api, space.id) == "repairing"


def test_verify_unqualified_keeps_occupation_active(api, make_space, make_occupation):
    space = make_space()
    occupation = make_occupation(space=space)
    api.data(_approve(api, occupation.id))

    data = api.data(_verify(api, occupation.id, verify_result="unqualified",
                            verify_comment="恢复面积不足，需整改"))
    assert data["status"] == "approved"
    assert data["verify_result"] == "unqualified"
    assert _space_status(api, space.id) == "occupied"

    # 整改后可再次核验，合格后占用结束
    data = api.data(_verify(api, occupation.id))
    assert data["status"] == "completed"
    assert _space_status(api, space.id) == "normal"


def test_verify_only_allowed_when_approved(api, make_occupation):
    occupation = make_occupation()
    assert _verify(api, occupation.id).status_code == 409

    api.data(_approve(api, occupation.id))
    api.data(_verify(api, occupation.id))
    assert _verify(api, occupation.id).status_code == 409


def test_verification_requires_area_and_plants(api, make_occupation):
    occupation = make_occupation()
    api.data(_approve(api, occupation.id))
    response = api.patch(f"/api/v1/green-occupations/{occupation.id}/verification",
                         {"verify_result": "qualified", "verified_by": "沈建国"})
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "restored_area_sqm" in details
    assert "plant_restoration" in details


# ------------------------------------------------------------ 列表与汇总
def test_list_filters_and_summary(api, make_space, make_occupation):
    space = make_space()
    expired_space = make_space(name="超期绿地")
    make_occupation(space=space, category="event", reason="市集活动占用")
    approved = make_occupation(space=space, category="pipeline", reason="管线敷设占用")
    api.data(_approve(api, approved.id))
    make_occupation(space=expired_space, category="construction",
                    start_date=date(2019, 12, 1), end_date=date(2020, 1, 1),
                    reason="历史遗留占用")
    expired = make_occupation(space=expired_space, category="construction",
                              start_date=date(2026, 2, 1),
                              end_date=date.today() - timedelta(days=1))
    api.data(_approve(api, expired.id))

    data = api.data(api.get("/api/v1/green-occupations"))
    assert data["meta"]["total"] == 4
    summary = data["summary"]
    assert summary["by_status"]["pending"] == 2
    assert summary["by_status"]["approved"] == 2
    assert summary["expired_count"] == 1

    data = api.data(api.get("/api/v1/green-occupations", status="approved"))
    assert data["meta"]["total"] == 2
    data = api.data(api.get("/api/v1/green-occupations", category="event"))
    assert data["meta"]["total"] == 1
    data = api.data(api.get("/api/v1/green-occupations", keyword="管线"))
    assert data["meta"]["total"] == 1
    data = api.data(api.get("/api/v1/green-occupations", expired="true"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["is_expired"] is True
    data = api.data(api.get("/api/v1/green-occupations", green_space_id=space.id))
    assert data["meta"]["total"] == 2


# ------------------------------------------------------------ 跨模块联动
def test_occupied_space_excluded_from_assessment(api, make_space, make_task, make_record,
                                                 make_occupation):
    """占绿中的绿地不参与养护考核：不进工作量排名，逾期任务不计入提醒。"""

    occupied_space = make_space(name="占绿绿地")
    normal_space = make_space(name="正常绿地")
    yesterday = date.today() - timedelta(days=1)
    make_task(space=occupied_space, plan_date=yesterday, status="pending")
    make_task(space=normal_space, plan_date=yesterday, status="pending")
    make_record(space=occupied_space)
    make_record(space=normal_space)

    occupation = make_occupation(space=occupied_space)
    api.data(_approve(api, occupation.id))

    overview = api.data(api.get("/api/v1/statistics/overview"))
    assert overview["task"]["overdue_count"] == 1

    reminders = api.data(api.get("/api/v1/statistics/reminders"))
    assert len(reminders["overdue"]) == 1
    assert reminders["overdue"][0]["green_space_id"] == normal_space.id

    ranking = api.data(api.get("/api/v1/statistics/ranking"))["items"]
    ranked_ids = {item["green_space_id"] for item in ranking}
    assert normal_space.id in ranked_ids
    assert occupied_space.id not in ranked_ids

    # 占绿期间档案不再提示养护逾期
    profile = api.data(api.get(f"/api/v1/green-spaces/{occupied_space.id}/profile"))
    assert profile["statistics"]["is_maintenance_overdue"] is False


def test_profile_exposes_occupation_info(api, make_space, make_occupation):
    space = make_space()
    occupation = make_occupation(space=space)
    api.data(_approve(api, occupation.id))

    profile = api.data(api.get(f"/api/v1/green-spaces/{space.id}/profile"))
    assert profile["current_occupation"]["occupation_no"] == occupation.occupation_no
    assert profile["statistics"]["occupation_status"]["approved"] == 1
    assert len(profile["recent_occupations"]) == 1

    api.data(_verify(api, occupation.id))
    profile = api.data(api.get(f"/api/v1/green-spaces/{space.id}/profile"))
    assert profile["current_occupation"] is None
    assert profile["statistics"]["occupation_status"]["completed"] == 1


def test_green_space_delete_protection_counts_occupations(api, make_space, make_occupation):
    space = make_space()
    make_occupation(space=space)

    response = api.delete(f"/api/v1/green-spaces/{space.id}")
    assert response.status_code == 409
    assert response.get_json()["data"]["green_space_occupation"] == 1

    data = api.data(api.delete(f"/api/v1/green-spaces/{space.id}", force="true"))
    assert data["green_space_occupation"] == 1
    assert api.get(f"/api/v1/green-occupations", green_space_id=space.id) \
        .get_json()["data"]["meta"]["total"] == 0


def test_seed_includes_occupation_demo_data(api, seeded):
    assert seeded["green_space_occupation"] == 4

    data = api.data(api.get("/api/v1/green-occupations", page_size=100))
    assert data["meta"]["total"] == 4
    by_status = data["summary"]["by_status"]
    assert by_status == {"pending": 1, "approved": 1, "rejected": 1, "completed": 1}

    # 演示数据自洽：占绿中的绿地恰为生效占用所在绿地
    spaces = api.data(api.get("/api/v1/green-spaces", status="occupied"))
    assert spaces["summary"]["total"] == 1
    occupied_id = spaces["items"][0]["id"]
    active = api.data(api.get("/api/v1/green-occupations", status="approved"))
    assert active["items"][0]["green_space_id"] == occupied_id
