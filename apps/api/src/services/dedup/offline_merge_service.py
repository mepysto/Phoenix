"""Offline merge service for batch deduplication of existing events."""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import ColumnElement, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from sqlalchemy.orm import selectinload

from src.db.database import engine
from src.models.event import Dataset, Event, EventMetric, EventSource, EventType, GeoLayer
from src.services.dedup.quality import QualityScorer

ColumnExpr = ColumnElement[bool]

logger = logging.getLogger(__name__)

ADVISORY_LOCK_ID = 12345


@dataclass
class OfflineMergeConfig:
    chunk_size: int = 1000
    fuzzy_radius_meters: int = 50_000
    fuzzy_window_hours: int = 48
    max_group_size: int = 200
    progress_log_every: int = 100
    dry_run: bool = False


@dataclass
class OfflineMergeStats:
    scanned: int = 0
    groups_found: int = 0
    merges_applied: int = 0
    sources_relinked: int = 0
    geo_layers_relinked: int = 0
    datasets_relinked: int = 0
    metrics_relinked: int = 0
    duplicates_marked: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


ScopeType = Literal["all", "active", "inactive"]


class OfflineMergeService:
    def __init__(
        self,
        session: AsyncSession,
        config: OfflineMergeConfig | None = None,
    ):
        self.session = session
        self.config = config or OfflineMergeConfig()
        self.quality_scorer = QualityScorer()
        self._lock_connection: AsyncConnection | None = None

    async def run(
        self,
        *,
        scope: ScopeType = "all",
        since: datetime | None = None,
        event_types: list[EventType] | None = None,
    ) -> OfflineMergeStats:
        stats = OfflineMergeStats()

        if not await self.acquire_lock():
            stats.errors.append("Failed to acquire advisory lock - another merge job may be running")
            return stats

        try:
            groups = await self.find_duplicate_groups(
                scope=scope,
                since=since,
                event_types=event_types,
            )
            stats.groups_found = len(groups)

            for i, group in enumerate(groups):
                if len(group) > self.config.max_group_size:
                    logger.warning(
                        f"Skipping group with {len(group)} events (exceeds max_group_size={self.config.max_group_size})"
                    )
                    stats.skipped += 1
                    continue

                try:
                    merge_stats = await self.resolve_group(group)
                    stats.merges_applied += merge_stats.get("merges", 0)
                    stats.sources_relinked += merge_stats.get("sources_relinked", 0)
                    stats.geo_layers_relinked += merge_stats.get("geo_layers_relinked", 0)
                    stats.datasets_relinked += merge_stats.get("datasets_relinked", 0)
                    stats.metrics_relinked += merge_stats.get("metrics_relinked", 0)
                    stats.duplicates_marked += merge_stats.get("duplicates_marked", 0)
                    stats.scanned += len(group)

                    if not self.config.dry_run:
                        await self.session.commit()
                except Exception as e:
                    logger.exception(f"Error resolving group {group}: {e}")
                    stats.errors.append(f"Group {group[:3]}...: {str(e)}")
                    await self.session.rollback()
                    continue

                if (i + 1) % self.config.progress_log_every == 0:
                    logger.info(
                        f"Progress: {i + 1}/{len(groups)} groups processed, "
                        f"{stats.merges_applied} merges applied"
                    )

        finally:
            await self.release_lock()

        return stats

    async def acquire_lock(self) -> bool:
        self._lock_connection = await engine.connect()
        result = await self._lock_connection.execute(
            text(f"SELECT pg_try_advisory_lock({ADVISORY_LOCK_ID})")
        )
        acquired = result.scalar()
        if acquired:
            logger.info(f"Acquired advisory lock {ADVISORY_LOCK_ID}")
            return True
        else:
            logger.warning(f"Failed to acquire advisory lock {ADVISORY_LOCK_ID}")
            await self._lock_connection.close()
            self._lock_connection = None
            return False

    async def release_lock(self) -> None:
        if self._lock_connection is not None:
            try:
                await self._lock_connection.execute(
                    text(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_ID})")
                )
                logger.info(f"Released advisory lock {ADVISORY_LOCK_ID}")
            finally:
                await self._lock_connection.close()
                self._lock_connection = None

    async def find_duplicate_groups(
        self,
        *,
        scope: ScopeType = "all",
        since: datetime | None = None,
        event_types: list[EventType] | None = None,
    ) -> list[list[UUID]]:
        groups: list[list[UUID]] = []
        seen_event_ids: set[UUID] = set()

        strong_key_groups = await self._find_strong_key_groups(
            scope=scope, since=since, event_types=event_types
        )
        for group in strong_key_groups:
            filtered = [eid for eid in group if eid not in seen_event_ids]
            if len(filtered) > 1:
                groups.append(filtered)
                seen_event_ids.update(filtered)

        fuzzy_groups = await self._find_fuzzy_groups(
            scope=scope, since=since, event_types=event_types, exclude_ids=seen_event_ids
        )
        for group in fuzzy_groups:
            filtered = [eid for eid in group if eid not in seen_event_ids]
            if len(filtered) > 1:
                groups.append(filtered)
                seen_event_ids.update(filtered)

        return groups

    async def _find_strong_key_groups(
        self,
        *,
        scope: ScopeType = "all",
        since: datetime | None = None,
        event_types: list[EventType] | None = None,
    ) -> list[list[UUID]]:
        conditions: list[ColumnExpr] = [
            Event.glide_number.isnot(None),
            Event.is_canonical.is_(True),
            Event.merged_into_id.is_(None),
        ]

        if scope == "active":
            conditions.append(Event.is_active.is_(True))
        elif scope == "inactive":
            conditions.append(Event.is_active.is_(False))

        if since:
            conditions.append(Event.created_at >= since)  # type: ignore[arg-type]

        if event_types:
            conditions.append(Event.type.in_(event_types))

        stmt = (
            select(Event.glide_number, func.array_agg(Event.id))
            .where(*conditions)
            .group_by(Event.glide_number)
            .having(func.count(Event.id) > 1)
            .having(func.count(Event.id) <= self.config.max_group_size)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [list(row[1]) for row in rows]

    async def _find_fuzzy_groups(
        self,
        *,
        scope: ScopeType = "all",
        since: datetime | None = None,
        event_types: list[EventType] | None = None,
        exclude_ids: set[UUID] | None = None,
    ) -> list[list[UUID]]:
        groups: list[list[UUID]] = []
        exclude_ids = exclude_ids or set()
        processed_ids: set[UUID] = set()

        last_start_date: datetime | None = None
        last_id: UUID | None = None

        while True:
            events = await self._fetch_fuzzy_candidates_page(
                scope=scope,
                since=since,
                event_types=event_types,
                exclude_ids=exclude_ids | processed_ids,
                cursor_start_date=last_start_date,
                cursor_id=last_id,
            )

            if not events:
                break

            for event in events:
                if event.id in processed_ids or event.id in exclude_ids:
                    continue

                group = await self._expand_connected_component(
                    seed_event=event,
                    exclude_ids=exclude_ids | processed_ids,
                )

                if len(group) > 1:
                    if len(group) <= self.config.max_group_size:
                        groups.append(group)
                    else:
                        logger.warning(
                            f"Skipping oversized fuzzy group with {len(group)} events"
                        )
                    processed_ids.update(group)

            last_event = events[-1]
            last_start_date = last_event.start_date
            last_id = last_event.id

        return groups

    async def _fetch_fuzzy_candidates_page(
        self,
        *,
        scope: ScopeType,
        since: datetime | None,
        event_types: list[EventType] | None,
        exclude_ids: set[UUID],
        cursor_start_date: datetime | None,
        cursor_id: UUID | None,
    ) -> list[Event]:
        conditions: list[ColumnExpr] = [
            Event.is_canonical.is_(True),
            Event.merged_into_id.is_(None),
            Event.location.isnot(None),
        ]

        if scope == "active":
            conditions.append(Event.is_active.is_(True))
        elif scope == "inactive":
            conditions.append(Event.is_active.is_(False))

        if since:
            conditions.append(Event.created_at >= since)  # type: ignore[arg-type]

        if event_types:
            conditions.append(Event.type.in_(event_types))

        if exclude_ids:
            conditions.append(Event.id.notin_(exclude_ids))

        if cursor_start_date is not None and cursor_id is not None:
            conditions.append(
                (Event.start_date < cursor_start_date) |  # type: ignore[arg-type]
                ((Event.start_date == cursor_start_date) & (Event.id < cursor_id))  # type: ignore[arg-type]
            )

        stmt = (
            select(Event)
            .where(*conditions)
            .order_by(Event.start_date.desc(), Event.id.desc())
            .limit(self.config.chunk_size)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _expand_connected_component(
        self,
        seed_event: Event,
        exclude_ids: set[UUID],
    ) -> list[UUID]:
        group_ids: set[UUID] = {seed_event.id}
        queue: deque[Event] = deque([seed_event])

        while queue:
            if len(group_ids) > self.config.max_group_size:
                break

            current = queue.popleft()
            candidates = await self._find_spatiotemporal_candidates(
                current, exclude_ids=exclude_ids | group_ids
            )

            for candidate in candidates:
                if candidate.id not in group_ids and candidate.id not in exclude_ids:
                    group_ids.add(candidate.id)
                    queue.append(candidate)

                    if len(group_ids) > self.config.max_group_size:
                        break

        return list(group_ids)

    async def _find_spatiotemporal_candidates(
        self,
        reference: Event,
        exclude_ids: set[UUID] | None = None,
    ) -> list[Event]:
        if reference.latitude is None or reference.longitude is None:
            return []

        exclude_ids = exclude_ids or set()
        time_delta = timedelta(hours=self.config.fuzzy_window_hours)
        min_date = reference.start_date - time_delta
        max_date = reference.start_date + time_delta

        from src.utils.geo import point_within_distance

        conditions = [
            Event.id != reference.id,
            Event.type == reference.type,
            Event.is_canonical.is_(True),
            Event.merged_into_id.is_(None),
            Event.location.isnot(None),
            Event.start_date >= min_date,
            Event.start_date <= max_date,
            point_within_distance(
                Event.location,
                reference.latitude,
                reference.longitude,
                self.config.fuzzy_radius_meters,
            ),
        ]

        if exclude_ids:
            conditions.append(Event.id.notin_(exclude_ids))  # type: ignore[arg-type]

        stmt = select(Event).where(*conditions)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def resolve_group(self, event_ids: list[UUID]) -> dict[str, int]:
        stats = {
            "merges": 0,
            "sources_relinked": 0,
            "geo_layers_relinked": 0,
            "datasets_relinked": 0,
            "metrics_relinked": 0,
            "duplicates_marked": 0,
        }

        if len(event_ids) < 2:
            return stats

        stmt = (
            select(Event)
            .where(Event.id.in_(event_ids))
            .options(selectinload(Event.sources).selectinload(EventSource.source))
        )
        result = await self.session.execute(stmt)
        events = list(result.scalars().all())

        if len(events) < 2:
            return stats

        canonical = self._select_canonical(events)
        duplicates = [e for e in events if e.id != canonical.id]

        logger.debug(
            f"Resolving group: canonical={canonical.id}, duplicates={[d.id for d in duplicates]}"
        )

        for duplicate in duplicates:
            if self.config.dry_run:
                logger.info(
                    f"[DRY-RUN] Would merge {duplicate.id} into {canonical.id}"
                )
                stats["duplicates_marked"] += 1
                continue

            relinked = await self.relink_sources(duplicate.id, canonical.id)
            stats["sources_relinked"] += relinked

            children_relinked = await self.relink_children(duplicate.id, canonical.id)
            stats["geo_layers_relinked"] += children_relinked["geo_layers"]
            stats["datasets_relinked"] += children_relinked["datasets"]
            stats["metrics_relinked"] += children_relinked["event_metrics"]

            await self.mark_merged(duplicate.id, canonical.id)
            stats["duplicates_marked"] += 1

        stats["merges"] = 1 if duplicates else 0
        return stats

    def _select_canonical(self, events: list[Event]) -> Event:
        scored_events: list[tuple[Event, float]] = []

        for event in events:
            source_name = None
            if event.sources:
                first_source = event.sources[0]
                source_name = first_source.source.name if first_source.source else None

            quality = self.quality_scorer.score_existing(event, source_name)
            scored_events.append((event, quality.total))

        scored_events.sort(key=lambda x: x[1], reverse=True)
        return scored_events[0][0]

    async def relink_sources(self, from_event_id: UUID, to_event_id: UUID) -> int:
        if self.config.dry_run:
            count_stmt = select(func.count(EventSource.id)).where(
                EventSource.event_id == from_event_id
            )
            result = await self.session.execute(count_stmt)
            return result.scalar() or 0

        stmt = (
            update(EventSource)
            .where(EventSource.event_id == from_event_id)
            .values(event_id=to_event_id)
            .returning(EventSource.id)
        )
        result = await self.session.execute(stmt)
        return len(result.all())

    async def relink_children(
        self, from_event_id: UUID, to_event_id: UUID
    ) -> dict[str, int]:
        """Relink all child records (GeoLayer, Dataset, EventMetric) from duplicate to canonical.

        Returns dict with counts: {"geo_layers": N, "datasets": N, "event_metrics": N}
        """
        counts: dict[str, int] = {"geo_layers": 0, "datasets": 0, "event_metrics": 0}

        counts["geo_layers"] = await self._relink_geo_layers(from_event_id, to_event_id)
        counts["datasets"] = await self._relink_datasets(from_event_id, to_event_id)
        counts["event_metrics"] = await self._relink_event_metrics(from_event_id, to_event_id)

        return counts

    async def _relink_geo_layers(self, from_event_id: UUID, to_event_id: UUID) -> int:
        if self.config.dry_run:
            count_stmt = select(func.count(GeoLayer.id)).where(
                GeoLayer.event_id == from_event_id
            )
            result = await self.session.execute(count_stmt)
            return result.scalar() or 0

        stmt = (
            update(GeoLayer)
            .where(GeoLayer.event_id == from_event_id)
            .values(event_id=to_event_id)
            .returning(GeoLayer.id)
        )
        result = await self.session.execute(stmt)
        return len(result.all())

    async def _relink_datasets(self, from_event_id: UUID, to_event_id: UUID) -> int:
        if self.config.dry_run:
            count_stmt = select(func.count(Dataset.id)).where(
                Dataset.event_id == from_event_id
            )
            result = await self.session.execute(count_stmt)
            return result.scalar() or 0

        stmt = (
            update(Dataset)
            .where(Dataset.event_id == from_event_id)
            .values(event_id=to_event_id)
            .returning(Dataset.id)
        )
        result = await self.session.execute(stmt)
        return len(result.all())

    async def _relink_event_metrics(self, from_event_id: UUID, to_event_id: UUID) -> int:
        """EventMetric has composite PK (time, event_id, metric_type).
        Deletes conflicting metrics before relinking to avoid PK violation.
        """
        if self.config.dry_run:
            count_stmt = select(func.count()).select_from(EventMetric).where(
                EventMetric.event_id == from_event_id
            )
            result = await self.session.execute(count_stmt)
            return result.scalar() or 0

        from sqlalchemy import and_, delete, exists

        canonical_metrics = (
            select(EventMetric.time, EventMetric.metric_type)
            .where(EventMetric.event_id == to_event_id)
            .subquery()
        )

        delete_conflicts_stmt = (
            delete(EventMetric)
            .where(
                EventMetric.event_id == from_event_id,
                exists(
                    select(1)
                    .select_from(canonical_metrics)
                    .where(
                        and_(
                            canonical_metrics.c.time == EventMetric.time,
                            canonical_metrics.c.metric_type == EventMetric.metric_type,
                        )
                    )
                ),
            )
        )
        await self.session.execute(delete_conflicts_stmt)

        stmt = (
            update(EventMetric)
            .where(EventMetric.event_id == from_event_id)
            .values(event_id=to_event_id)
            .returning(EventMetric.event_id)
        )
        result = await self.session.execute(stmt)
        return len(result.all())

    async def mark_merged(self, duplicate_id: UUID, canonical_id: UUID) -> None:
        if self.config.dry_run:
            return

        stmt = (
            update(Event)
            .where(Event.id == duplicate_id)
            .values(
                merged_into_id=canonical_id,
                is_canonical=False,
                is_active=False,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
