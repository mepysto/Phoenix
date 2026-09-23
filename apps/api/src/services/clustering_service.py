from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.event import Event, EventSource, EventType, SeverityLevel
from src.schemas.event import (
    ClusterBBox,
    ClusterResponse,
    DataSourceRef,
    DisplayPoint,
    EventCluster,
    EventFilter,
    EventResponse,
    Location,
)


SEVERITY_RANK: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class ClusteringService:
    ZOOM_TO_PRECISION: dict[tuple[int, int], int] = {
        (0, 4): 2,
        (4, 7): 3,
        (7, 10): 4,
        (10, 13): 5,
        (13, 15): 6,
    }

    MIN_CLUSTER_SIZE = 2

    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_precision_for_zoom(self, zoom: int) -> int:
        for (min_zoom, max_zoom), precision in self.ZOOM_TO_PRECISION.items():
            if min_zoom <= zoom < max_zoom:
                return precision
        return 7

    async def get_clusters(
        self,
        zoom: int,
        filters: EventFilter,
    ) -> ClusterResponse:
        if zoom >= 15:
            return await self._get_unclustered(filters)

        precision = self._get_precision_for_zoom(zoom)
        return await self._get_clustered(precision, filters, zoom)

    async def _get_unclustered(self, filters: EventFilter) -> ClusterResponse:
        stmt = select(Event).where(Event.location.isnot(None))
        stmt = self._apply_filters(stmt, filters)
        stmt = stmt.options(
            selectinload(Event.sources).selectinload(EventSource.source)
        )
        stmt = stmt.order_by(Event.start_date.desc()).limit(1000)

        result = await self.session.execute(stmt)
        events = list(result.scalars().all())

        event_responses = [self._to_event_response(e) for e in events]

        return ClusterResponse(
            zoom=15,
            clusters=[],
            unclustered=event_responses,
            total_events=len(event_responses),
            total_clusters=0,
        )

    async def _get_clustered(
        self,
        precision: int,
        filters: EventFilter,
        zoom: int,
    ) -> ClusterResponse:
        geohash_expr = func.ST_GeoHash(Event.location, precision)

        cluster_query = (
            select(
                geohash_expr.label("geohash"),
                func.count(Event.id).label("event_count"),
                func.ST_Y(func.ST_Centroid(func.ST_Collect(Event.location))).label("center_lat"),
                func.ST_X(func.ST_Centroid(func.ST_Collect(Event.location))).label("center_lng"),
                func.min(Event.latitude).label("min_lat"),
                func.max(Event.latitude).label("max_lat"),
                func.min(Event.longitude).label("min_lng"),
                func.max(Event.longitude).label("max_lng"),
                func.array_agg(Event.type).label("event_types"),
                func.array_agg(Event.severity).label("severities"),
                func.array_agg(Event.id).label("event_ids"),
            )
            .where(Event.location.isnot(None))
        )

        cluster_query = self._apply_filters(cluster_query, filters)
        cluster_query = cluster_query.group_by(geohash_expr)

        result = await self.session.execute(cluster_query)
        rows = result.fetchall()

        clusters: list[EventCluster] = []
        unclustered_ids: list[Any] = []

        for row in rows:
            event_count = row.event_count
            if event_count >= self.MIN_CLUSTER_SIZE:
                event_types_count = self._count_event_types(row.event_types)
                max_severity = self._get_max_severity(row.severities)

                cluster = EventCluster(
                    cluster_id=f"cluster_{row.geohash}",
                    center_lat=row.center_lat,
                    center_lng=row.center_lng,
                    count=event_count,
                    bbox=ClusterBBox(
                        min_lat=row.min_lat,
                        max_lat=row.max_lat,
                        min_lng=row.min_lng,
                        max_lng=row.max_lng,
                    ),
                    event_types=event_types_count,
                    max_severity=max_severity,
                )
                clusters.append(cluster)
            else:
                unclustered_ids.extend(row.event_ids)

        unclustered: list[EventResponse] = []
        if unclustered_ids:
            unclustered_stmt = (
                select(Event)
                .where(Event.id.in_(unclustered_ids))
                .options(
                    selectinload(Event.sources).selectinload(EventSource.source)
                )
            )
            unclustered_result = await self.session.execute(unclustered_stmt)
            unclustered_events = list(unclustered_result.scalars().all())
            unclustered = [self._to_event_response(e) for e in unclustered_events]

        total_events = sum(c.count for c in clusters) + len(unclustered)

        return ClusterResponse(
            zoom=zoom,
            clusters=clusters,
            unclustered=unclustered,
            total_events=total_events,
            total_clusters=len(clusters),
        )

    def _apply_filters(self, stmt: Any, filters: EventFilter) -> Any:
        conditions = []

        if filters.types:
            type_enums = [EventType(t) for t in filters.types]
            conditions.append(Event.type.in_(type_enums))

        if filters.severities:
            severity_enums = [SeverityLevel(s) for s in filters.severities]
            conditions.append(Event.severity.in_(severity_enums))

        if filters.is_active is not None:
            conditions.append(Event.is_active == filters.is_active)

        if not filters.include_merged:
            conditions.append(Event.is_canonical.is_(True))

        if filters.start_date:
            conditions.append(Event.start_date >= filters.start_date)

        if filters.end_date:
            conditions.append(Event.start_date <= filters.end_date)

        if all(
            v is not None
            for v in [filters.min_lng, filters.min_lat, filters.max_lng, filters.max_lat]
        ):
            conditions.append(Event.longitude >= filters.min_lng)
            conditions.append(Event.longitude <= filters.max_lng)
            conditions.append(Event.latitude >= filters.min_lat)
            conditions.append(Event.latitude <= filters.max_lat)

        for condition in conditions:
            stmt = stmt.where(condition)

        return stmt

    def _count_event_types(self, event_types: list[EventType]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for et in event_types:
            type_value = et.value if isinstance(et, EventType) else str(et)
            counts[type_value] = counts.get(type_value, 0) + 1
        return counts

    def _get_max_severity(self, severities: list[SeverityLevel]) -> str | None:
        if not severities:
            return None

        max_severity: str | None = None
        max_rank = 0

        for sev in severities:
            sev_value = sev.value if isinstance(sev, SeverityLevel) else str(sev)
            rank = SEVERITY_RANK.get(sev_value, 0)
            if rank > max_rank:
                max_rank = rank
                max_severity = sev_value

        return max_severity

    def _to_event_response(self, event: Event) -> EventResponse:
        location = Location(
            lat=event.latitude,
            lng=event.longitude,
            country=event.region,
            country_code=event.country_code,
        )

        display_point = None
        if event.latitude is not None and event.longitude is not None:
            display_point = DisplayPoint(
                lat=event.latitude,
                lng=event.longitude,
                source="event",
            )

        sources: list[DataSourceRef] = []
        try:
            for es in event.sources:
                if es.source:
                    sources.append(
                        DataSourceRef(
                            id=es.source.id,
                            name=es.source.name,
                            type=es.source.type,
                        )
                    )
        except Exception:
            pass

        return EventResponse(
            id=event.id,
            type=event.type.value,
            title=event.title,
            description=event.description,
            location=location,
            geo_precision=event.geo_precision.value if event.geo_precision else None,
            display_point=display_point,
            severity=event.severity.value,
            affected_population=event.affected_population,
            start_date=event.start_date,
            end_date=event.end_date,
            is_active=event.is_active,
            sources=sources,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
