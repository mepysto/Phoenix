"""Critical infrastructure within a map viewport (dams, power plants)."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.infrastructure import InfrastructureAsset

router = APIRouter()

AssetKind = Literal["dam", "power_plant"]
MAX_FEATURES = 5000


def _envelope(min_lng: float, min_lat: float, max_lng: float, max_lat: float) -> Any:
    return func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)


def viewport_filter(min_lng: float, min_lat: float, max_lng: float, max_lat: float) -> Any:
    """Bounding-box test on the GiST-indexed point; a box crossing the
    antimeridian (min_lng > max_lng) is split into its two halves."""
    location = InfrastructureAsset.location
    if min_lng <= max_lng:
        return location.op("&&")(_envelope(min_lng, min_lat, max_lng, max_lat))
    return or_(
        location.op("&&")(_envelope(min_lng, min_lat, 180, max_lat)),
        location.op("&&")(_envelope(-180, min_lat, max_lng, max_lat)),
    )


@router.get("")
async def infrastructure_in_view(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    min_lng: Annotated[float, Query(ge=-180, le=180)],
    min_lat: Annotated[float, Query(ge=-90, le=90)],
    max_lng: Annotated[float, Query(ge=-180, le=180)],
    max_lat: Annotated[float, Query(ge=-90, le=90)],
    kinds: Annotated[list[AssetKind] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_FEATURES)] = 2000,
) -> dict[str, Any]:
    """Dams and power plants in the viewport as GeoJSON, most significant
    first (MW / dam height). `truncated` means zoom in to see the rest."""
    stmt = (
        select(
            InfrastructureAsset.kind,
            InfrastructureAsset.name,
            InfrastructureAsset.country,
            InfrastructureAsset.importance,
            InfrastructureAsset.attributes,
            func.ST_X(InfrastructureAsset.location).label("lng"),
            func.ST_Y(InfrastructureAsset.location).label("lat"),
        )
        .where(viewport_filter(min_lng, min_lat, max_lng, max_lat))
        .order_by(InfrastructureAsset.importance.desc().nulls_last())
        .limit(limit + 1)  # one extra row tells us whether we truncated
    )
    if kinds:
        stmt = stmt.where(InfrastructureAsset.kind.in_(kinds))
    rows = (await session.execute(stmt)).all()

    # Reference data changes rarely; let browsers/CDNs reuse viewport results
    response.headers["Cache-Control"] = "public, max-age=3600"
    return {
        "type": "FeatureCollection",
        "truncated": len(rows) > limit,
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(r.lng, 5), round(r.lat, 5)]},
                "properties": {
                    "kind": r.kind,
                    "name": r.name,
                    "country": r.country,
                    "importance": r.importance,
                    **r.attributes,
                },
            }
            for r in rows[:limit]
        ],
    }
