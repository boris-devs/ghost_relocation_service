"""Алгоритм подбора места переселения для привидения.

Чистые функции без обращения к базе данных — принимают и возвращают объекты
SQLAlchemy-моделей (app.db.models.Ghost / app.db.models.Location), но НЕ трогают
сессию и не делают запросов, поэтому их легко тестировать напрямую (см.
backend/tests/test_matching.py), просто создавая Ghost(...)/Location(...)
без сохранения в базу.

Идея алгоритма:
1. Для пары (привидение, место) сначала проверяются "жёсткие" условия
   (capacity, дедлайн, явные конфликты вроде "боится зеркал" + "есть зеркала").
   Если хоть одно нарушено — место отбрасывается, причина запоминается.
2. Для мест, прошедших жёсткие условия, считается "мягкий" рейтинг 0..100
   из нескольких взвешенных компонентов (температура, шум/тревожность,
   влажность, теснота) — чем выше, тем лучше подходит место.
3. Для пакетной обработки заявки обрабатываются в порядке срочности
   (ближайший дедлайн → выше тревожность), чтобы более срочные и
   тревожные привидения не остались без места из-за того, что свободные
   места разобрали менее срочные заявки.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.db.enums import Humidity, Lighting, SpecialCondition
from app.db.models import Ghost, Location

WEIGHT_TEMPERATURE = 35
WEIGHT_NOISE = 35
WEIGHT_DAMPNESS = 15
WEIGHT_CROWDING = 15


@dataclass
class HardCheckResult:
    ok: bool
    reasons: list[str]


@dataclass
class ScoredCandidate:
    location: Location
    score: float
    explanation: list[str]


@dataclass
class MatchOutcome:
    ghost: Ghost
    best: ScoredCandidate | None
    rejected: list[tuple[Location, list[str]]] = field(default_factory=list)
    impossible_reason: str | None = None


def check_hard_constraints(ghost: Ghost, location: Location, today: date) -> HardCheckResult:
    """Возвращает жёсткие несовместимости места с заявкой (если есть)."""
    reasons: list[str] = []

    if location.free_capacity <= 0:
        reasons.append("в месте нет свободных мест (переполнено)")

    conditions = set(ghost.special_conditions)

    if SpecialCondition.NEEDS_ATTIC in conditions and not location.has_attic:
        reasons.append("привидению нужен чердак, а в этом месте его нет")

    if SpecialCondition.FEARS_MIRRORS in conditions and location.has_mirrors:
        reasons.append("привидение боится зеркал, а в этом месте они есть")

    if SpecialCondition.NO_HUMANS_NEARBY in conditions and location.has_people:
        reasons.append("привидению нельзя жить рядом с людьми, а в этом месте они бывают")

    if SpecialCondition.NEEDS_DARKNESS in conditions and location.lighting == Lighting.BRIGHT:
        reasons.append("в этом месте слишком светло")

    if SpecialCondition.NEEDS_SILENCE in conditions and location.noise_level > 3:
        reasons.append("привидению нужна тишина, а в этом месте слишком шумно")

    for restriction in location.restrictions:
        if restriction == "no_new_arrivals":
            reasons.append("место не принимает новых жильцов (ограничение)")

    return HardCheckResult(ok=not reasons, reasons=reasons)


def score_candidate(ghost: Ghost, location: Location) -> ScoredCandidate:
    """Считает мягкий рейтинг места для заявки, прошедшей жёсткие условия."""
    explanation: list[str] = []

    temp_diff = abs(location.ambient_temperature - ghost.favorite_temperature)
    temp_score = max(0.0, 100 - temp_diff * 8)
    if temp_diff <= 1:
        explanation.append(
            f"температура почти совпадает с любимой ({location.ambient_temperature:.0f}°C "
            f"против {ghost.favorite_temperature:.0f}°C)"
        )
    elif temp_diff <= 4:
        explanation.append(f"температура близка к любимой (разница {temp_diff:.0f}°C)")
    else:
        explanation.append(f"температура сильно отличается от любимой (разница {temp_diff:.0f}°C)")

    comfortable_noise = max(0, 10 - ghost.anxiety_level)
    noise_diff = abs(location.noise_level - comfortable_noise)
    noise_score = max(0.0, 100 - noise_diff * 12)
    if ghost.anxiety_level >= 7:
        if location.noise_level <= 3:
            explanation.append("тихое место хорошо подходит тревожному привидению")
        else:
            explanation.append("привидение тревожное, а здесь довольно шумно")
    else:
        explanation.append("уровень шума в целом подходит")

    likes_damp = SpecialCondition.LIKES_DAMPNESS in set(ghost.special_conditions)

    if likes_damp and location.humidity == Humidity.DAMP:
        dampness_score = 100.0
        explanation.append("учтена любовь к сырости — здесь сыро")
    elif likes_damp and location.humidity == Humidity.NORMAL:
        dampness_score = 60.0
    elif likes_damp:
        dampness_score = 20.0
        explanation.append("привидение любит сырость, а здесь сухо")
    else:
        dampness_score = 80.0  

    dislikes_crowds = SpecialCondition.DISLIKES_CROWDS in set(ghost.special_conditions)
    occupancy_ratio = location.occupied / location.capacity if location.capacity else 1.0
    if dislikes_crowds:
        crowding_score = max(0.0, 100 - occupancy_ratio * 100)
        if occupancy_ratio >= 0.7:
            explanation.append("привидение не любит тесноту, а место почти заполнено")
        else:
            explanation.append("свободного места достаточно для непривычного к тесноте привидения")
    else:
        crowding_score = 70.0

    total = (
        temp_score * WEIGHT_TEMPERATURE
        + noise_score * WEIGHT_NOISE
        + dampness_score * WEIGHT_DAMPNESS
        + crowding_score * WEIGHT_CROWDING
    ) / 100

    return ScoredCandidate(location=location, score=round(total, 1), explanation=explanation)


def match_ghost(ghost: Ghost, locations: list[Location], today: date) -> MatchOutcome:
    """Подбирает лучшее место для одной заявки среди списка мест."""
    if today > ghost.relocation_deadline:
        return MatchOutcome(ghost=ghost, best=None, impossible_reason="дедлайн переселения просрочен")

    if not locations:
        return MatchOutcome(
            ghost=ghost,
            best=None,
            impossible_reason="нет ни одного зарегистрированного места переселения",
        )

    rejected: list[tuple[Location, list[str]]] = []
    candidates: list[ScoredCandidate] = []

    for location in locations:
        check = check_hard_constraints(ghost, location, today)
        if not check.ok:
            rejected.append((location, check.reasons))
            continue
        candidates.append(score_candidate(ghost, location))

    if not candidates:
        return MatchOutcome(
            ghost=ghost, best=None, rejected=rejected, impossible_reason=_summarize_rejection(rejected)
        )

    best = max(candidates, key=lambda c: c.score)
    return MatchOutcome(ghost=ghost, best=best, rejected=rejected, impossible_reason=None)


def _summarize_rejection(rejected: list[tuple[Location, list[str]]]) -> str:
    """Выбирает краткую главную причину невозможности переселения."""
    if not rejected:
        return "подходящих мест не найдено"

    reason_counts: dict[str, int] = {}
    for _location, reasons in rejected:
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    most_common = max(reason_counts.items(), key=lambda kv: kv[1])[0]
    if len(rejected) == 1:
        location, reasons = rejected[0]
        return f"{location.name}: {', '.join(reasons)}"
    return f"{most_common} (во всех {len(rejected)} рассмотренных местах)"


def match_all(ghosts: list[Ghost], locations: list[Location], today: date) -> list[MatchOutcome]:
    """Пакетный подбор: обрабатывает заявки по срочности, чтобы места
    доставались в первую очередь самым срочным и тревожным привидениям."""

    if not ghosts:
        return []

    working_locations = {loc.id: _clone_location(loc) for loc in locations}

    ordered_ghosts = sorted(ghosts, key=lambda g: (g.relocation_deadline, -g.anxiety_level))

    outcomes: list[MatchOutcome] = []
    for ghost in ordered_ghosts:
        outcome = match_ghost(ghost, list(working_locations.values()), today)
        if outcome.best is not None:
            working_locations[outcome.best.location.id].occupied += 1
        outcomes.append(outcome)

    order_index = {g.id: i for i, g in enumerate(ghosts)}
    outcomes.sort(key=lambda o: order_index.get(o.ghost.id, 0))
    return outcomes


def _clone_location(location: Location) -> Location:
    """Лёгкая транзиентная копия места — никогда не добавляется в сессию,
    существует только для симуляции внутри пакетного подбора."""
    return Location(
        id=location.id,
        name=location.name,
        location_type=location.location_type,
        capacity=location.capacity,
        occupied=location.occupied,
        lighting=location.lighting,
        noise_level=location.noise_level,
        humidity=location.humidity,
        ambient_temperature=location.ambient_temperature,
        has_people=location.has_people,
        has_mirrors=location.has_mirrors,
        has_attic=location.has_attic,
        restrictions=list(location.restrictions),
    )


@dataclass
class ManualCheckResult:
    hard_conflicts: list[str]
    warnings: list[str]


def validate_manual_choice(ghost: Ghost, location: Location, today: date) -> ManualCheckResult:
    """Проверяет ручной выбор места оператором.

    Жёсткие конфликты (hard_conflicts) — это те же условия, что и в
    автоматическом алгоритме (переполненность, явные противопоказания).
    Предупреждения (warnings) — субъективно плохой, но не запрещённый выбор
    (например, температура сильно отличается от любимой).
    """
    check = check_hard_constraints(ghost, location, today)
    warnings: list[str] = []

    if today > ghost.relocation_deadline:
        check.reasons.append("дедлайн переселения уже просрочен")

    scored = score_candidate(ghost, location)
    if scored.score < 40:
        warnings.append(f"место плохо подходит по совокупности параметров (рейтинг {scored.score}/100)")
    temp_diff = abs(location.ambient_temperature - ghost.favorite_temperature)
    if temp_diff > 8:
        warnings.append(f"температура сильно отличается от любимой (разница {temp_diff:.0f}°C)")
    if ghost.anxiety_level >= 7 and location.noise_level >= 6:
        warnings.append("привидение тревожное, а место шумное")
    if SpecialCondition.LIKES_DAMPNESS in set(ghost.special_conditions) and location.humidity == Humidity.DRY:
        warnings.append("привидение любит сырость, а здесь сухо")
    if (
        SpecialCondition.DISLIKES_CROWDS in set(ghost.special_conditions)
        and location.capacity
        and location.occupied / location.capacity >= 0.8
    ):
        warnings.append("привидение не любит тесноту, а место почти заполнено")

    return ManualCheckResult(hard_conflicts=check.reasons, warnings=warnings)


def condition_label(condition: SpecialCondition) -> str:
    from app.db.enums import SPECIAL_CONDITION_LABELS

    return SPECIAL_CONDITION_LABELS.get(condition, condition.value)
