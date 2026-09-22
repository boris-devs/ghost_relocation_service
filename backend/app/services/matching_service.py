"""Оркестрация подбора мест: соединяет репозитории (доступ к данным) и
чистый алгоритм (app.services.algorithm), владеет транзакцией."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import Assignment, Ghost, Location
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.ghost_repository import GhostRepository
from app.repositories.location_repository import LocationRepository
from app.schemas import AssignmentOut, ManualAssignRequest, ManualAssignResponse, MatchResultOut
from app.services import algorithm
from app.services.exceptions import NotFoundError


class MatchingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ghosts = GhostRepository(session)
        self.locations = LocationRepository(session)
        self.assignments = AssignmentRepository(session)


    async def current_status(self) -> list[MatchResultOut]:
        """Уже сохранённые назначения (автоматические или ручные) — как есть; для
        ещё не распределённых заявок — лучшее предложение, посчитанное пакетно (с
        учётом того, что несколько заявок могут претендовать на одно и то же
        место), но пока ничего никуда не записанное — запись происходит либо
        через кнопку «Обновить предложения» (run_matching), либо вручную
        (manual_assign)."""
        ghost_records = await self.ghosts.list_all()
        location_records = await self.locations.list_all()
        assignments = {a.ghost_id: a for a in await self.assignments.list_all()}
        location_by_id = {loc.id: loc for loc in location_records}
        today = date.today()
        logger.debug(
            "current_status(): заявок={} мест={} уже сохранённых назначений={}",
            len(ghost_records), len(location_records), len(assignments),
        )

        results: list[MatchResultOut] = []
        unassigned_ghosts: list[Ghost] = []

        for ghost in ghost_records:
            assignment = assignments.get(ghost.id)
            if assignment is not None:
                loc = location_by_id[assignment.location_id]
                results.append(
                    _matched_result(
                        ghost, loc, assignment.score, assignment.explanation, assignment.manual, assignment.warnings,
                        assigned=True,
                    )
                )
            else:
                unassigned_ghosts.append(ghost)

        outcomes = algorithm.match_all(unassigned_ghosts, location_records, today)
        for outcome in outcomes:
            if outcome.best is not None:
                loc = location_by_id[outcome.best.location.id]
                results.append(
                    _matched_result(
                        ghost=outcome.ghost, location=loc, score=outcome.best.score,
                        explanation=outcome.best.explanation, manual=False, warnings=[],
                        assigned=False,
                    )
                )
            else:
                results.append(_impossible_result(outcome.ghost, outcome))

        order_index = {g.id: i for i, g in enumerate(ghost_records)}
        results.sort(key=lambda r: order_index.get(r.ghost_id, 0))
        return results


    async def run_matching(self) -> list[MatchResultOut]:
        """Кнопка «Обновить предложения»: реально назначает места всем ещё не
        распределённым заявкам — пакетно (algorithm.match_all), с учётом того,
        что несколько заявок могут конкурировать за одно и то же место. Уже
        существующие ручные назначения (assignment.manual = True) не трогает —
        только автоматические, посчитанные на предыдущем запуске."""
        logger.info("run_matching: старт")
        ghost_records = await self.ghosts.list_all()
        location_records = await self.locations.list_all()
        assignment_records = await self.assignments.list_all()
        location_by_id = {loc.id: loc for loc in location_records}
        logger.info(
            "run_matching: заявок={} мест={} уже назначений={}",
            len(ghost_records), len(location_records), len(assignment_records),
        )

        manual_ghost_ids = {a.ghost_id for a in assignment_records if a.manual}

        deleted_count = 0
        for assignment in assignment_records:
            if not assignment.manual:
                location_by_id[assignment.location_id].occupied -= 1
                await self.assignments.delete(assignment)
                deleted_count += 1
        await self.session.flush()
        logger.info("run_matching: удалено старых авто-назначений={}", deleted_count)

        today = date.today()
        auto_ghosts = [g for g in ghost_records if g.id not in manual_ghost_ids]
        outcomes = algorithm.match_all(auto_ghosts, location_records, today)

        created_count = 0
        for outcome in outcomes:
            if outcome.best is not None:
                location = location_by_id[outcome.best.location.id]
                location.occupied += 1
                self.assignments.add(
                    Assignment(
                        ghost_id=outcome.ghost.id,
                        location_id=location.id,
                        score=outcome.best.score,
                        explanation=outcome.best.explanation,
                        manual=False,
                        warnings=[],
                    )
                )
                created_count += 1
                logger.debug(
                    "run_matching: {} -> {} (score={})",
                    outcome.ghost.name, location.name, outcome.best.score,
                )
            else:
                logger.debug(
                    "run_matching: {} осталась без места ({})",
                    outcome.ghost.name, outcome.impossible_reason,
                )

        try:
            await self.session.commit()
        except Exception:
            logger.exception("run_matching: commit() упал с исключением, изменения НЕ сохранены")
            raise
        logger.info(
            "run_matching: создано новых авто-назначений={}, ручных не тронуто={} — коммит выполнен",
            created_count, len(manual_ghost_ids),
        )
        return await self.current_status()


    async def manual_assign(self, payload: ManualAssignRequest) -> ManualAssignResponse:
        logger.info(
            "manual_assign: ghost_id={} -> location_id={} (force={})",
            payload.ghost_id, payload.location_id, payload.force,
        )
        ghost = await self.ghosts.get(payload.ghost_id)
        if ghost is None:
            raise NotFoundError("Заявка привидения не найдена")
        target_location = await self.locations.get(payload.location_id)
        if target_location is None:
            raise NotFoundError("Место переселения не найдено")

        location_records = await self.locations.list_all()
        location_by_id = {loc.id: loc for loc in location_records}

        existing = ghost.assignment
        if existing is not None:
            location_by_id[existing.location_id].occupied -= 1

        check = algorithm.validate_manual_choice(ghost, location_by_id[payload.location_id], date.today())

        if check.hard_conflicts:
            if existing is not None:
                location_by_id[existing.location_id].occupied += 1
            logger.warning("manual_assign: заблокировано жёсткими условиями: {}", check.hard_conflicts)
            return ManualAssignResponse(status="blocked", hard_conflicts=check.hard_conflicts, warnings=check.warnings)

        if check.warnings and not payload.force:
            if existing is not None:
                location_by_id[existing.location_id].occupied += 1
            logger.info("manual_assign: нужно подтверждение, предупреждения: {}", check.warnings)
            return ManualAssignResponse(status="needs_confirmation", warnings=check.warnings)

        if existing is not None:
            await self.assignments.delete(existing)
            await self.session.flush()

        scored = algorithm.score_candidate(ghost, location_by_id[payload.location_id])
        new_assignment = Assignment(
            ghost_id=ghost.id,
            location_id=target_location.id,
            score=scored.score,
            explanation=scored.explanation,
            manual=True,
            warnings=check.warnings,
        )
        self.assignments.add(new_assignment)
        target_location.occupied += 1
        try:
            await self.session.commit()
        except Exception:
            logger.exception("manual_assign: commit() упал с исключением, изменения НЕ сохранены")
            raise
        logger.info(
            "manual_assign: сохранено — ghost_id={} -> {} (score={})",
            ghost.id, target_location.name, scored.score,
        )

        return ManualAssignResponse(
            status="assigned",
            assignment=AssignmentOut(
                location_id=target_location.id,
                location_name=target_location.name,
                score=scored.score,
                explanation=scored.explanation,
                manual=True,
                warnings=check.warnings,
            ),
            warnings=check.warnings,
        )


    async def unassign(self, ghost_id: int) -> None:
        logger.info("unassign: ghost_id={}", ghost_id)
        ghost = await self.ghosts.get(ghost_id)
        if ghost is None:
            raise NotFoundError("Заявка привидения не найдена")
        if ghost.assignment is None:
            logger.debug("unassign: у ghost_id={} и так не было назначения", ghost_id)
            return
        location = await self.locations.get(ghost.assignment.location_id)
        if location is not None:
            location.occupied = max(0, location.occupied - 1)
        await self.assignments.delete(ghost.assignment)
        await self.session.commit()
        logger.info("unassign: назначение для ghost_id={} удалено", ghost_id)


def _matched_result(
    ghost: Ghost,
    location: Location,
    score: float,
    explanation: list[str],
    manual: bool,
    warnings: list[str],
    *,
    assigned: bool,
) -> MatchResultOut:
    return MatchResultOut(
        ghost_id=ghost.id,
        ghost_name=ghost.name,
        status="matched",
        assigned=assigned,
        assignment=AssignmentOut(
            location_id=location.id,
            location_name=location.name,
            score=score,
            explanation=explanation,
            manual=manual,
            warnings=warnings,
        ),
    )


def _impossible_result(ghost: Ghost, outcome: algorithm.MatchOutcome) -> MatchResultOut:
    return MatchResultOut(
        ghost_id=ghost.id,
        ghost_name=ghost.name,
        status="impossible",
        impossible_reason=outcome.impossible_reason,
        rejected_locations=[{"location_name": loc.name, "reasons": reasons} for loc, reasons in outcome.rejected],
    )
