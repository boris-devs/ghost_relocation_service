from datetime import date, timedelta

import pytest


@pytest.mark.asyncio
async def test_empty_ghost_list_returns_empty_array(client):
    resp = await client.get("/api/ghosts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_ghost_and_location_then_run_matching(client):
    ghost_resp = await client.post(
        "/api/ghosts",
        json={
            "name": "Матильда",
            "anxiety_level": 3,
            "favorite_temperature": 12,
            "relocation_deadline": str(date.today() + timedelta(days=10)),
            "special_conditions": [],
        },
    )
    assert ghost_resp.status_code == 201

    location_resp = await client.post(
        "/api/locations",
        json={
            "name": "Тихий подвал",
            "location_type": "подвал",
            "capacity": 3,
            "occupied": 0,
            "lighting": "dim",
            "noise_level": 1,
            "humidity": "normal",
            "ambient_temperature": 12,
            "has_people": False,
            "has_mirrors": False,
            "has_attic": False,
            "restrictions": [],
        },
    )
    assert location_resp.status_code == 201

    run_resp = await client.post("/api/match/run")
    assert run_resp.status_code == 200
    results = run_resp.json()
    assert len(results) == 1
    assert results[0]["status"] == "matched"
    assert results[0]["assignment"]["location_name"] == "Тихий подвал"
    # Регрессия: MatchResultOut раньше не объявлял поле "assigned", поэтому
    # pydantic молча отбрасывал его при сериализации, и фронтенд никогда не
    # получал assigned=true даже для реально сохранённого автоназначения.
    assert results[0]["assigned"] is True
    assert results[0]["assignment"]["manual"] is False


@pytest.mark.asyncio
async def test_match_status_shows_unassigned_preview_before_run_then_persists_after(client):
    """До нажатия «Обновить предложения» GET /api/match отдаёт превью лучшего
    места (assigned=false, ничего не сохранено). После запуска подбора то же
    привидение должно быть уже назначено (assigned=true) — и повторный GET
    отдаёт именно сохранённое назначение, а не снова пересчитанное превью."""
    await client.post(
        "/api/ghosts",
        json={
            "name": "Сквозняк",
            "anxiety_level": 3,
            "favorite_temperature": 12,
            "relocation_deadline": str(date.today() + timedelta(days=10)),
            "special_conditions": [],
        },
    )
    await client.post(
        "/api/locations",
        json={
            "name": "Пустой чердак",
            "location_type": "чердак",
            "capacity": 2,
            "occupied": 0,
            "lighting": "dim",
            "noise_level": 1,
            "humidity": "normal",
            "ambient_temperature": 12,
            "has_people": False,
            "has_mirrors": False,
            "has_attic": True,
            "restrictions": [],
        },
    )

    before = await client.get("/api/match")
    assert before.status_code == 200
    before_results = before.json()
    assert len(before_results) == 1
    assert before_results[0]["status"] == "matched"
    assert before_results[0]["assigned"] is False
    assert before_results[0]["assignment"]["location_name"] == "Пустой чердак"

    run_resp = await client.post("/api/match/run")
    assert run_resp.status_code == 200

    after = await client.get("/api/match")
    after_results = after.json()
    assert after_results[0]["assigned"] is True
    assert after_results[0]["assignment"]["manual"] is False
    assert after_results[0]["assignment"]["location_name"] == "Пустой чердак"


@pytest.mark.asyncio
async def test_ghost_with_no_suitable_location_is_reported_impossible(client):
    await client.post(
        "/api/ghosts",
        json={
            "name": "Одинокий дух",
            "anxiety_level": 5,
            "favorite_temperature": 12,
            "relocation_deadline": str(date.today() + timedelta(days=10)),
            "special_conditions": ["needs_attic"],
        },
    )
    await client.post(
        "/api/locations",
        json={
            "name": "Место без чердака",
            "location_type": "театр",
            "capacity": 2,
            "occupied": 0,
            "lighting": "dim",
            "noise_level": 2,
            "humidity": "normal",
            "ambient_temperature": 12,
            "has_people": False,
            "has_mirrors": False,
            "has_attic": False,
            "restrictions": [],
        },
    )

    run_resp = await client.post("/api/match/run")
    results = run_resp.json()
    assert results[0]["status"] == "impossible"
    assert "чердак" in results[0]["impossible_reason"]
    assert results[0]["assigned"] is False


@pytest.mark.asyncio
async def test_overcrowded_location_blocks_manual_assignment(client):
    ghost_resp = await client.post(
        "/api/ghosts",
        json={
            "name": "Новичок",
            "anxiety_level": 4,
            "favorite_temperature": 12,
            "relocation_deadline": str(date.today() + timedelta(days=10)),
            "special_conditions": [],
        },
    )
    ghost_id = ghost_resp.json()["id"]

    location_resp = await client.post(
        "/api/locations",
        json={
            "name": "Забитый маяк",
            "location_type": "маяк",
            "capacity": 1,
            "occupied": 1,  
            "lighting": "bright",
            "noise_level": 3,
            "humidity": "normal",
            "ambient_temperature": 12,
            "has_people": False,
            "has_mirrors": False,
            "has_attic": False,
            "restrictions": [],
        },
    )
    location_id = location_resp.json()["id"]

    manual_resp = await client.post(
        "/api/match/manual",
        json={"ghost_id": ghost_id, "location_id": location_id, "force": True},
    )
    assert manual_resp.status_code == 200
    body = manual_resp.json()
    assert body["status"] == "blocked"
    assert any("переполнено" in c for c in body["hard_conflicts"])


@pytest.mark.asyncio
async def test_manual_assignment_with_soft_warning_needs_confirmation_then_force(client):
    ghost_resp = await client.post(
        "/api/ghosts",
        json={
            "name": "Мерзлячка",
            "anxiety_level": 2,
            "favorite_temperature": 28,
            "relocation_deadline": str(date.today() + timedelta(days=10)),
            "special_conditions": [],
        },
    )
    ghost_id = ghost_resp.json()["id"]

    location_resp = await client.post(
        "/api/locations",
        json={
            "name": "Ледяной подвал",
            "location_type": "подвал",
            "capacity": 5,
            "occupied": 0,
            "lighting": "dark",
            "noise_level": 0,
            "humidity": "damp",
            "ambient_temperature": -5,
            "has_people": False,
            "has_mirrors": False,
            "has_attic": False,
            "restrictions": [],
        },
    )
    location_id = location_resp.json()["id"]

    first_try = await client.post(
        "/api/match/manual",
        json={"ghost_id": ghost_id, "location_id": location_id, "force": False},
    )
    assert first_try.json()["status"] == "needs_confirmation"
    assert first_try.json()["warnings"]

    forced = await client.post(
        "/api/match/manual",
        json={"ghost_id": ghost_id, "location_id": location_id, "force": True},
    )
    assert forced.json()["status"] == "assigned"
    assert forced.json()["assignment"]["manual"] is True

    status_resp = await client.get("/api/match")
    status_body = status_resp.json()
    assert status_body[0]["assigned"] is True
    assert status_body[0]["assignment"]["manual"] is True


@pytest.mark.asyncio
async def test_run_matching_does_not_touch_existing_manual_assignment(client):
    """«Обновить предложения» должна расставлять места только ещё не
    назначенным заявкам и не трогать те, что уже закреплены вручную —
    именно на этом построен UI-тег «Подобрано ручным режимом»."""
    manual_ghost_resp = await client.post(
        "/api/ghosts",
        json={
            "name": "Уже пристроена",
            "anxiety_level": 3,
            "favorite_temperature": 12,
            "relocation_deadline": str(date.today() + timedelta(days=10)),
            "special_conditions": [],
        },
    )
    manual_ghost_id = manual_ghost_resp.json()["id"]

    manual_location_resp = await client.post(
        "/api/locations",
        json={
            "name": "Ручной домик",
            "location_type": "домик",
            "capacity": 2,
            "occupied": 0,
            "lighting": "dim",
            "noise_level": 1,
            "humidity": "normal",
            "ambient_temperature": 12,
            "has_people": False,
            # Специально с зеркалами: заявка, для которой запускаем автоподбор
            # ниже, боится зеркал, поэтому это место ей гарантированно не
            # подойдёт по жёсткому условию — так тест детерминирован и не
            # зависит от того, какое из двух одинаково подходящих мест
            # алгоритм выбрал бы при равном рейтинге.
            "has_mirrors": True,
            "has_attic": False,
            "restrictions": [],
        },
    )
    manual_location_id = manual_location_resp.json()["id"]

    manual_assign_resp = await client.post(
        "/api/match/manual",
        json={"ghost_id": manual_ghost_id, "location_id": manual_location_id, "force": False},
    )
    assert manual_assign_resp.json()["status"] == "assigned"

    auto_ghost_resp = await client.post(
        "/api/ghosts",
        json={
            "name": "Ещё не пристроена",
            "anxiety_level": 3,
            "favorite_temperature": 12,
            "relocation_deadline": str(date.today() + timedelta(days=10)),
            "special_conditions": ["fears_mirrors"],
        },
    )
    auto_ghost_id = auto_ghost_resp.json()["id"]

    await client.post(
        "/api/locations",
        json={
            "name": "Свободный сарай",
            "location_type": "сарай",
            "capacity": 2,
            "occupied": 0,
            "lighting": "dim",
            "noise_level": 1,
            "humidity": "normal",
            "ambient_temperature": 12,
            "has_people": False,
            "has_mirrors": False,
            "has_attic": False,
            "restrictions": [],
        },
    )

    run_resp = await client.post("/api/match/run")
    results = {r["ghost_id"]: r for r in run_resp.json()}

    manual_result = results[manual_ghost_id]
    assert manual_result["assigned"] is True
    assert manual_result["assignment"]["manual"] is True
    assert manual_result["assignment"]["location_name"] == "Ручной домик"

    auto_result = results[auto_ghost_id]
    assert auto_result["assigned"] is True
    assert auto_result["assignment"]["manual"] is False
    assert auto_result["assignment"]["location_name"] == "Свободный сарай"


@pytest.mark.asyncio
async def test_report_counts_relocated_and_unrelocated(client):
    await client.post(
        "/api/ghosts",
        json={
            "name": "Без места",
            "anxiety_level": 5,
            "favorite_temperature": 12,
            "relocation_deadline": str(date.today() + timedelta(days=10)),
            "special_conditions": ["needs_attic"],
        },
    )
    await client.post(
        "/api/locations",
        json={
            "name": "Без чердака",
            "location_type": "театр",
            "capacity": 2,
            "occupied": 0,
            "lighting": "dim",
            "noise_level": 2,
            "humidity": "normal",
            "ambient_temperature": 12,
            "has_people": False,
            "has_mirrors": False,
            "has_attic": False,
            "restrictions": [],
        },
    )
    await client.post("/api/match/run")

    report_resp = await client.get("/api/report")
    assert report_resp.status_code == 200
    body = report_resp.json()
    assert body["total_ghosts"] == 1
    assert body["unrelocated"] == 1
    assert body["relocated"] == 0
    assert len(body["most_problematic"]) == 1


@pytest.mark.asyncio
async def test_deleting_nonexistent_ghost_returns_clean_404(client):
    resp = await client.delete("/api/ghosts/999")
    assert resp.status_code == 404
    assert "detail" in resp.json()
