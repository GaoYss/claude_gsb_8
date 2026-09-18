"""占绿审批与恢复核验测试。"""

from datetime import date, timedelta


def occupation_payload(**overrides):
    today_ = date.today()
    payload = {
        "reason": "construction",
        "purpose": "地铁出入口配套施工临时占用绿地",
        "scope_description": "沿占用红线围挡施工，保留人行通道。",
        "occupy_area_sqm": 300,
        "start_date": (today_ + timedelta(days=2)).isoformat(),
        "end_date": (today_ + timedelta(days=32)).isoformat(),
        "applicant": "杭州地铁集团",
        "applicant_phone": "0571-88001122",
        "apply_date": (today_ - timedelta(days=5)).isoformat(),
        "restore_requirement": "占用期满拆除临时设施，按原苗木规格恢复绿化。",
    }
    payload.update(overrides)
    return payload


# ------------------------------------------------------------ 登记与校验
def test_create_occupation_generates_daily_code(api, make_space):
    space = make_space()
    data = api.data(
        api.post("/api/v1/occupations", occupation_payload(green_space_id=space.id)), 201
    )
    assert data["occupation_no"].startswith("OC-")
    assert data["occupation_no"].endswith("-001")
    assert data["status"] == "pending"
    assert data["status_label"] == "待审批"
    assert data["is_active"] is False
    assert data["occupy_area_sqm"] == 300.0
    assert data["green_space"]["id"] == space.id


def test_create_occupation_collects_field_errors(api, make_space):
    space = make_space()
    response = api.post("/api/v1/occupations", {
        "green_space_id": space.id,
        "reason": "not-a-reason",
        "purpose": "",
        "occupy_area_sqm": -10,
        "start_date": "2026-05-01",
        "end_date": "2026-04-01",
        "apply_date": "bad-date",
    })
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert set(details) == {
        "reason", "purpose", "occupy_area_sqm", "end_date", "apply_date",
    }


def test_occupy_area_cannot_exceed_green_space_area(api, make_space):
    space = make_space(area_sqm=500)
    response = api.post(
        "/api/v1/occupations", occupation_payload(green_space_id=space.id, occupy_area_sqm=600)
    )
    assert response.status_code == 422
    assert "occupy_area_sqm" in response.get_json()["data"]


def test_occupation_rejected_for_archived_space(api, make_space):
    space = make_space(status="archived")
    response = api.post(
        "/api/v1/occupations", occupation_payload(green_space_id=space.id)
    )
    assert response.status_code == 409
    assert "已归档" in response.get_json()["message"]


def test_only_pending_occupation_can_be_edited(api, make_occupation):
    occupation = make_occupation()
    approved = api.data(api.patch(
        f"/api/v1/occupations/{occupation.id}/approval",
        {"action": "approved", "approved_by": "方骏"},
    ))
    assert approved["status"] == "approved"

    response = api.put(
        f"/api/v1/occupations/{occupation.id}",
        occupation_payload(
            green_space_id=occupation.green_space_id,
            start_date=occupation.start_date.isoformat(),
            end_date=occupation.end_date.isoformat(),
            apply_date=occupation.apply_date.isoformat(),
            purpose="已审批后尝试修改",
        ),
    )
    assert response.status_code == 409
    assert "待审批" in response.get_json()["message"]


# ------------------------------------------------------------ 审批
def test_approval_marks_green_space_occupied(api, make_space):
    space = make_space()
    occupation = api.data(
        api.post("/api/v1/occupations", occupation_payload(
            green_space_id=space.id,
            start_date=date.today().isoformat(),
            end_date=(date.today() + timedelta(days=20)).isoformat(),
        )), 201
    )
    # 审批前绿地未占绿
    detail = api.data(api.get(f"/api/v1/green-spaces/{space.id}"))
    assert detail["is_occupied"] is False

    approved = api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/approval",
        {"action": "approved", "approved_by": "方骏", "approval_remark": "同意占用"},
    ))
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "方骏"

    detail = api.data(api.get(f"/api/v1/green-spaces/{space.id}"))
    assert detail["is_occupied"] is True
    assert detail["occupation_no"] == occupation["occupation_no"]


def test_future_start_occupation_does_not_mark_occupied_yet(api, make_space):
    space = make_space()
    occupation = api.data(
        api.post("/api/v1/occupations", occupation_payload(
            green_space_id=space.id,
            start_date=(date.today() + timedelta(days=10)).isoformat(),
            end_date=(date.today() + timedelta(days=40)).isoformat(),
        )), 201
    )
    api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/approval",
        {"action": "approved", "approved_by": "方骏"},
    ))
    detail = api.data(api.get(f"/api/v1/green-spaces/{space.id}"))
    # 尚未到占用开始日期，地块暂不标记占绿
    assert detail["is_occupied"] is False


def test_cannot_approve_two_active_occupations_on_same_space(api, make_occupation):
    first = make_occupation(
        start_date=date.today(), end_date=date.today() + timedelta(days=20)
    )
    api.data(api.patch(
        f"/api/v1/occupations/{first.id}/approval",
        {"action": "approved", "approved_by": "方骏"},
    ))

    second = make_occupation(
        space=first.green_space,
        start_date=date.today() + timedelta(days=5),
        end_date=date.today() + timedelta(days=25),
        apply_date=date.today() - timedelta(days=2),
    )
    response = api.patch(
        f"/api/v1/occupations/{second.id}/approval",
        {"action": "approved", "approved_by": "方骏"},
    )
    assert response.status_code == 409
    assert "已有生效中的占绿记录" in response.get_json()["message"]


def test_reject_occupation_does_not_mark_space(api, make_space):
    space = make_space()
    occupation = api.data(
        api.post("/api/v1/occupations", occupation_payload(green_space_id=space.id)), 201
    )
    rejected = api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/approval",
        {"action": "rejected", "approved_by": "方骏", "approval_remark": "红线不符"},
    ))
    assert rejected["status"] == "rejected"
    detail = api.data(api.get(f"/api/v1/green-spaces/{space.id}"))
    assert detail["is_occupied"] is False


def test_invalid_approval_action_rejected(api, make_occupation):
    occupation = make_occupation()
    response = api.patch(
        f"/api/v1/occupations/{occupation.id}/approval",
        {"action": "verified", "approved_by": "方骏"},
    )
    assert response.status_code == 422


def test_cannot_review_non_pending_occupation(api, make_occupation):
    occupation = make_occupation()
    api.data(api.patch(
        f"/api/v1/occupations/{occupation.id}/approval",
        {"action": "rejected", "approved_by": "方骏"},
    ))
    response = api.patch(
        f"/api/v1/occupations/{occupation.id}/approval",
        {"action": "approved", "approved_by": "方骏"},
    )
    assert response.status_code == 409


# ------------------------------------------------------------ 恢复报备与核验
def _approved_occupation(api, space, **dates):
    today_ = date.today()
    start = dates.get("start", today_ - timedelta(days=20))
    end = dates.get("end", today_ - timedelta(days=2))
    occupation = api.data(api.post("/api/v1/occupations", occupation_payload(
        green_space_id=space.id,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        apply_date=(start - timedelta(days=7)).isoformat(),
    )), 201)
    api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/approval",
        {"action": "approved", "approved_by": "方骏"},
    ))
    return occupation


def test_full_restore_verify_workflow_releases_green_space(api, make_space):
    space = make_space()
    occupation = _approved_occupation(api, space)

    # 占绿期间地块被标记
    assert api.data(api.get(f"/api/v1/green-spaces/{space.id}"))["is_occupied"] is True

    restored = api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/restore",
        {
            "restored_date": date.today().isoformat(),
            "restored_area_sqm": 300,
            "restored_plants": "恢复香樟 6 株、草坪 260 平方米。",
        },
    ))
    assert restored["status"] == "restored"
    # 待核验期间仍占绿、继续豁免考核
    assert api.data(api.get(f"/api/v1/green-spaces/{space.id}"))["is_occupied"] is True

    verified = api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/verify",
        {"verified_by": "高敏", "verify_remark": "恢复达标"},
    ))
    assert verified["status"] == "verified"
    assert verified["verified_by"] == "高敏"
    detail = api.data(api.get(f"/api/v1/green-spaces/{space.id}"))
    assert detail["is_occupied"] is False
    assert detail["occupation_no"] is None


def test_verify_fails_when_restored_area_short(api, make_space):
    space = make_space()
    occupation = _approved_occupation(api, space)
    api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/restore",
        {
            "restored_date": date.today().isoformat(),
            "restored_area_sqm": 250,
            "restored_plants": "恢复部分苗木。",
        },
    ))
    response = api.patch(
        f"/api/v1/occupations/{occupation['id']}/verify",
        {"verified_by": "高敏"},
    )
    assert response.status_code == 409
    details = response.get_json()["data"]
    assert "restored_area_sqm" in details
    assert "50.00" in details["restored_area_sqm"]
    # 核验不通过，仍处于待核验（继续占绿）
    detail = api.data(api.get(f"/api/v1/occupations/{occupation['id']}"))
    assert detail["status"] == "restored"


def test_verify_fails_without_plant_restore_record(app, make_space):
    """苗木恢复情况缺失时 service 兜底拒绝核验（绕过报备接口直接构造脏数据）。"""

    from app.services import OccupationService

    occupation = _approved_occupation_via_service(make_space)
    occupation.restored_date = date.today()
    occupation.restored_area_sqm = 300
    occupation.restored_plants = "   "
    occupation.status = "restored"

    from app.extensions import db
    db.session.commit()
    with app.test_request_context():
        from app.errors import ApiError
        try:
            OccupationService.verify(occupation.id, {"verified_by": "高敏"})
            assert False, "应当核验失败"
        except ApiError as exc:
            assert exc.status_code == 409
            assert "restored_plants" in exc.details


def _approved_occupation_via_service(make_space):
    from app.services import OccupationService

    space = make_space()
    occupation = OccupationService.create({
        "green_space_id": space.id,
        "reason": "construction",
        "purpose": "施工占用",
        "occupy_area_sqm": 300,
        "start_date": date.today() - timedelta(days=20),
        "end_date": date.today() - timedelta(days=2),
        "apply_date": date.today() - timedelta(days=27),
    })
    OccupationService.approve(occupation.id, {"action": "approved", "approved_by": "方骏"})
    return occupation


def test_restore_then_correct_and_verify(api, make_space):
    """面积不足核验被拒 -> 整改后重新报备达标 -> 核验通过。"""

    space = make_space()
    occupation = _approved_occupation(api, space)

    def report(area, plants):
        return api.patch(
            f"/api/v1/occupations/{occupation['id']}/restore",
            {
                "restored_date": date.today().isoformat(),
                "restored_area_sqm": area,
                "restored_plants": plants,
            },
        )

    api.data(report(250, "部分恢复"))
    assert api.patch(
        f"/api/v1/occupations/{occupation['id']}/verify",
        {"verified_by": "高敏"},
    ).status_code == 409

    api.data(report(300, "补植到位，恢复香樟 6 株、草坪 260 平方米。"))
    verified = api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/verify",
        {"verified_by": "高敏"},
    ))
    assert verified["status"] == "verified"


def test_verify_requires_restored_state(api, make_occupation):
    occupation = make_occupation()
    response = api.patch(
        f"/api/v1/occupations/{occupation.id}/verify",
        {"verified_by": "高敏"},
    )
    assert response.status_code == 409


def test_report_restore_requires_approved_state(api, make_occupation):
    occupation = make_occupation()
    response = api.patch(
        f"/api/v1/occupations/{occupation.id}/restore",
        {
            "restored_date": date.today().isoformat(),
            "restored_area_sqm": 300,
            "restored_plants": "恢复苗木",
        },
    )
    assert response.status_code == 409


# ------------------------------------------------------------ 删除保护
def test_delete_rules(api, make_occupation):
    # 待审批可删除
    pending = make_occupation()
    api.data(api.delete(f"/api/v1/occupations/{pending.id}"))
    assert api.get(f"/api/v1/occupations/{pending.id}").status_code == 404

    # 占绿中不可删除
    active = make_occupation(
        start_date=date.today(), end_date=date.today() + timedelta(days=10),
        apply_date=date.today() - timedelta(days=3),
    )
    api.data(api.patch(
        f"/api/v1/occupations/{active.id}/approval",
        {"action": "approved", "approved_by": "方骏"},
    ))
    response = api.delete(f"/api/v1/occupations/{active.id}")
    assert response.status_code == 409

    # 已驳回可删除
    rejected = make_occupation()
    api.data(api.patch(
        f"/api/v1/occupations/{rejected.id}/approval",
        {"action": "rejected", "approved_by": "方骏"},
    ))
    api.data(api.delete(f"/api/v1/occupations/{rejected.id}"))


def test_verified_occupation_is_permanent_record(api, make_space):
    space = make_space()
    occupation = _approved_occupation(api, space)
    api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/restore",
        {
            "restored_date": date.today().isoformat(),
            "restored_area_sqm": 300,
            "restored_plants": "恢复苗木",
        },
    ))
    api.data(api.patch(
        f"/api/v1/occupations/{occupation['id']}/verify",
        {"verified_by": "高敏"},
    ))
    response = api.delete(f"/api/v1/occupations/{occupation['id']}")
    assert response.status_code == 409
    assert "履历" in response.get_json()["message"]


def test_delete_green_space_blocked_while_occupied(api, make_space):
    space = make_space()
    _approved_occupation(api, space)
    response = api.delete(f"/api/v1/green-spaces/{space.id}", force="true")
    assert response.status_code == 409
    assert "占绿" in response.get_json()["message"]


# ------------------------------------------------------------ 列表过滤与汇总
def test_list_filters_and_summary(api, make_space):
    space_a = make_space(name="占绿绿地甲")
    space_b = make_space(name="普通绿地乙")
    occupation_a = _approved_occupation(api, space_a)
    # 另一条待审批
    api.data(api.post("/api/v1/occupations", occupation_payload(
        green_space_id=space_b.id,
        start_date=(date.today() + timedelta(days=3)).isoformat(),
        end_date=(date.today() + timedelta(days=33)).isoformat(),
    )), 201)

    listing = api.data(api.get("/api/v1/occupations", green_space_id=space_a.id))
    assert listing["meta"]["total"] == 1
    assert listing["items"][0]["id"] == occupation_a["id"]

    approved_only = api.data(api.get("/api/v1/occupations", status="approved"))
    assert approved_only["meta"]["total"] == 1

    data = api.data(api.get("/api/v1/occupations", page_size=50))
    assert data["meta"]["total"] == 2
    summary = data["summary"]
    assert summary["by_status"]["approved"]["count"] == 1
    assert summary["by_status"]["pending"]["count"] == 1
    assert summary["active_count"] == 1
    assert summary["active_area_sqm"] == 300.0


def test_overdue_restore_filter(api, make_space):
    space = make_space()
    occupation = _approved_occupation(
        api, space,
        start=date.today() - timedelta(days=40),
        end=date.today() - timedelta(days=5),
    )
    data = api.data(api.get("/api/v1/occupations", overdue_restore="true"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["id"] == occupation["id"]
    assert data["summary"]["overdue_restore_count"] == 1


# ------------------------------------------------------------ 养护考核豁免
def test_occupied_green_space_excluded_from_maintenance_assessment(api, make_space, make_task):
    occupied_space = make_space(name="占绿施工绿地")
    normal_space = make_space(name="正常养护绿地")
    _approved_occupation(api, occupied_space)

    # 两块绿地各有一条逾期任务
    make_task(space=occupied_space, plan_date=date.today() - timedelta(days=6), status="pending")
    make_task(space=normal_space, plan_date=date.today() - timedelta(days=6), status="pending")

    overview = api.data(api.get("/api/v1/statistics/overview"))
    assert overview["task"]["overdue_count"] == 1
    assert overview["occupation"]["active_count"] == 1
    assert overview["occupation"]["excluded_green_space_count"] == 1
    assert overview["green_space"]["occupied_count"] == 1

    reminders = api.data(api.get("/api/v1/statistics/reminders"))
    overdue_spaces = {item["green_space"]["id"] for item in reminders["overdue"]}
    assert occupied_space.id not in overdue_spaces
    assert normal_space.id in overdue_spaces
    assert set(reminders["occupations"]) == {"overdue_restore", "pending_verify"}


def test_occupied_green_space_excluded_from_ranking(api, make_space, make_record):
    occupied_space = make_space(name="占绿高频绿地")
    make_record(space=occupied_space)
    make_record(space=occupied_space, record_date=date(2026, 4, 2))
    normal_space = make_space(name="正常高频绿地")
    make_record(space=normal_space)

    # 尚未占绿：占绿绿地排第 1
    ranking = api.data(api.get("/api/v1/statistics/ranking", limit=10))["items"]
    assert ranking[0]["name"] == "占绿高频绿地"

    _approved_occupation(api, occupied_space)
    ranking = api.data(api.get("/api/v1/statistics/ranking", limit=10))["items"]
    names = {item["name"] for item in ranking}
    assert "占绿高频绿地" not in names
    assert "正常高频绿地" in names


def test_profile_reflects_occupation_and_exempts_overdue(api, make_space):
    space = make_space()
    occupation = _approved_occupation(api, space)
    profile = api.data(api.get(f"/api/v1/green-spaces/{space.id}/profile"))
    assert profile["statistics"]["is_occupied"] is True
    assert profile["active_occupation"]["occupation_no"] == occupation["occupation_no"]
    assert profile["recent_occupations"][0]["id"] == occupation["id"]
    # 占绿期间不判养护逾期
    assert profile["statistics"]["is_maintenance_overdue"] is False


# ------------------------------------------------------------ 种子数据
def test_demo_seed_covers_all_occupation_statuses(api, seeded):
    assert seeded["green_space_occupation"] == 6
    data = api.data(api.get("/api/v1/occupations", page_size=100))
    by_status = data["summary"]["by_status"]
    assert by_status["pending"]["count"] == 1
    assert by_status["approved"]["count"] == 2
    assert by_status["rejected"]["count"] == 1
    assert by_status["restored"]["count"] == 1
    assert by_status["verified"]["count"] == 1
    assert data["summary"]["active_count"] == 3
    assert data["summary"]["overdue_restore_count"] == 1


def test_enums_include_occupation_groups(api):
    enums = api.data(api.get("/api/v1/meta/enums"))["enums"]
    assert {"value": "construction", "label": "工程施工占用"} in enums["occupation_reason"]
    assert {v for v in (item["value"] for item in enums["occupation_status"])} == {
        "pending", "approved", "rejected", "restored", "verified",
    }
