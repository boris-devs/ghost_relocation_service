from datetime import date, timedelta

import pytest

from app.db.models import Ghost, Location
from app.services.algorithm import match_all, match_ghost, score_candidate, validate_manual_choice

TODAY = date(2026, 1, 1)


def make_location(**overrides) -> Location:
    defaults = dict(
        id=1,
        name="Тестовое место",
        location_type="замок",
        capacity=3,
        occupied=0,
        lighting="dim",
        noise_level=2,
        humidity="normal",
        ambient_temperature=12,
        has_people=False,
        has_mirrors=False,
        has_attic=False,
        restrictions=[],
    )
    defaults.update(overrides)
    return Location(**defaults)


def make_ghost(**overrides) -> Ghost:
    defaults = dict(
        id=1,
        name="Тестовое привидение",
        anxiety_level=5,
        favorite_temperature=12,
        relocation_deadline=TODAY + timedelta(days=10),
        special_conditions=[],
    )
    defaults.update(overrides)
    return Ghost(**defaults)


def test_matches_a_clearly_suitable_location():
    ghost = make_ghost(favorite_temperature=12, anxiety_level=8)
    location = make_location(ambient_temperature=12, noise_level=1)
    outcome = match_ghost(ghost, [location], TODAY)

    assert outcome.best is not None
    assert outcome.best.location.id == location.id
    assert outcome.impossible_reason is None
    assert len(outcome.best.explanation) > 0


def test_ghost_without_any_suitable_location_is_impossible():
    ghost = make_ghost(special_conditions=["needs_attic"])
    location_without_attic = make_location(has_attic=False)
    outcome = match_ghost(ghost, [location_without_attic], TODAY)

    assert outcome.best is None
    assert outcome.impossible_reason is not None
    assert "чердак" in outcome.impossible_reason


def test_full_location_is_rejected_for_capacity():
    ghost = make_ghost()
    full_location = make_location(capacity=2, occupied=2)
    outcome = match_ghost(ghost, [full_location], TODAY)

    assert outcome.best is None
    assert "переполнено" in outcome.impossible_reason


def test_past_deadline_is_always_impossible_even_with_perfect_location():
    ghost = make_ghost(relocation_deadline=TODAY - timedelta(days=1))
    perfect_location = make_location(ambient_temperature=ghost.favorite_temperature)
    outcome = match_ghost(ghost, [perfect_location], TODAY)

    assert outcome.best is None
    assert "дедлайн" in outcome.impossible_reason


def test_mirror_fear_conflicts_with_location_that_has_mirrors():
    ghost = make_ghost(special_conditions=["fears_mirrors"])
    mirrored_location = make_location(has_mirrors=True)
    outcome = match_ghost(ghost, [mirrored_location], TODAY)

    assert outcome.best is None
    assert "зеркал" in outcome.impossible_reason


def test_batch_matching_respects_capacity_across_multiple_ghosts():
    location = make_location(capacity=1, occupied=0)
    ghost_a = make_ghost(id=1, relocation_deadline=TODAY + timedelta(days=1))
    ghost_b = make_ghost(id=2, relocation_deadline=TODAY + timedelta(days=2))

    outcomes = match_all([ghost_a, ghost_b], [location], TODAY)
    matched = [o for o in outcomes if o.best is not None]
    unmatched = [o for o in outcomes if o.best is None]

    assert len(matched) == 1
    assert len(unmatched) == 1
    assert matched[0].ghost.id == ghost_a.id
    assert "переполнено" in unmatched[0].impossible_reason


def test_batch_matching_with_empty_ghost_list_returns_empty_result():
    location = make_location()
    outcomes = match_all([], [location], TODAY)
    assert outcomes == []


def test_manual_choice_flags_hard_conflict_for_full_location():
    ghost = make_ghost()
    full_location = make_location(capacity=1, occupied=1)
    result = validate_manual_choice(ghost, full_location, TODAY)

    assert result.hard_conflicts
    assert "переполнено" in result.hard_conflicts[0]


def test_manual_choice_warns_but_does_not_block_on_bad_temperature():
    ghost = make_ghost(favorite_temperature=25)
    cold_location = make_location(ambient_temperature=-5, capacity=5, occupied=0)
    result = validate_manual_choice(ghost, cold_location, TODAY)

    assert not result.hard_conflicts
    assert any("температура" in w for w in result.warnings)


@pytest.mark.parametrize("anxiety", [1, 5, 10])
def test_score_candidate_is_within_valid_range(anxiety):
    ghost = make_ghost(anxiety_level=anxiety)
    location = make_location()
    scored = score_candidate(ghost, location)
    assert 0 <= scored.score <= 100
