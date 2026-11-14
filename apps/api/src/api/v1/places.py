"""Place name search (GeoNames, CC BY 4.0) for choosing a location by name."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.place import Place, PlaceName

router = APIRouter()


class PlaceOut(BaseModel):
    id: int
    name: str
    admin1: str | None
    country: str | None
    country_code: str
    lat: float
    lng: float
    population: int


class PlaceSearchResponse(BaseModel):
    data: list[PlaceOut]
    attribution: str = "GeoNames (CC BY 4.0)"


def _like_prefix(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped}%"


@router.get("/search", response_model=PlaceSearchResponse)
async def search_places(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str, Query(min_length=2, max_length=100, description="Start of a place name, any language")],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> PlaceSearchResponse:
    """Places whose name in any language starts with `q`.

    Order: an exact name, then places whose main name starts with `q`, then
    by population.
    """
    needle = q.strip().casefold()
    exact = func.bool_or(PlaceName.name == literal(needle)).label("exact")
    matches = (
        select(PlaceName.place_id, exact)
        .where(PlaceName.name.like(_like_prefix(needle), escape="\\"))
        .group_by(PlaceName.place_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(Place)
            .join(matches, matches.c.place_id == Place.id)
            .order_by(
                matches.c.exact.desc(),
                # "seo" means Seoul before a bigger city with an obscure alternate name
                func.lower(Place.name).like(_like_prefix(needle), escape="\\").desc(),
                Place.population.desc(),
                Place.id,
            )
            .limit(limit)
        )
    ).scalars()
    # Place names change only on re-import
    response.headers["Cache-Control"] = "public, max-age=3600"
    return PlaceSearchResponse(
        data=[
            PlaceOut(
                id=p.id, name=p.name, admin1=p.admin1, country=p.country, country_code=p.country_code,
                lat=p.latitude, lng=p.longitude, population=p.population,
            )
            for p in rows
        ]
    )
