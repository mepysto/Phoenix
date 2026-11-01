"""Damage assessments from Copernicus EMS rapid mapping, kept per event.

Copernicus publishes, per activation, areas of interest (AOIs) and map
products with a damage grade. Phoenix stores each as a `damage` GeoLayer on
the event so the map and the event page can show *where* and *how badly*
places were hit, with a link to the source product.

Grades follow the EMS damage classes:
destroyed > damaged > possibly damaged > no visible damage (> unknown).
These are expert photo-interpretation results, not a Phoenix model.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import DataSource, Event, EventSource, GeoLayer
from src.services.copernicus_service import CopernicusEMSService, DamageAssessment
from src.utils.geojson import validate_geojson

logger = logging.getLogger(__name__)

LAYER_TYPE = "damage"
Grade = Literal["destroyed", "damaged", "possibly_damaged", "no_visible_damage", "unknown"]
GRADES: tuple[Grade, ...] = ("destroyed", "damaged", "possibly_damaged", "no_visible_damage", "unknown")

# Copernicus requests: be gentle with the public service
REQUEST_GAP_SECONDS = 1.0
MAX_EVENTS_PER_RUN = 15


def normalize_grade(raw: str | None) -> Grade:
    """Map the many spellings in EMS products onto the five classes."""
    if not raw:
        return "unknown"
    s = re.sub(r"[^a-z]+", " ", raw.lower()).strip()
    if not s:
        return "unknown"
    if "no visible" in s or s in {"none", "no damage", "not affected", "negligible"}:
        return "no_visible_damage"
    if "possibl" in s or "minor" in s or "slight" in s or "low" == s:
        return "possibly_damaged"
    if "destroy" in s or "complete" in s or "total" in s or "very high" in s:
        return "destroyed"
    if "damag" in s or "moderate" in s or "major" in s or "severe" in s or "high" == s or "medium" == s:
        return "damaged"
    return "unknown"


def _geometry(a: DamageAssessment) -> dict[str, Any] | None:
    geom = a.geometry
    if not isinstance(geom, dict) or "type" not in geom:
        return None
    ok, _errors = validate_geojson(geom)
    return geom if ok else None


def to_layers(event_id: UUID, assessments: Iterable[DamageAssessment]) -> list[GeoLayer]:
    """GeoLayer rows for the assessments that carry a valid geometry."""
    rows: list[GeoLayer] = []
    for a in assessments:
        geom = _geometry(a)
        if geom is None:
            continue
        rows.append(
            GeoLayer(
                event_id=event_id,
                layer_type=LAYER_TYPE,
                geojson=geom,
                properties={
                    "activation": a.activation_code,
                    "aoi_id": a.aoi_id,
                    "name": a.aoi_name,
                    "product_type": a.product_type,
                    "grade": normalize_grade(a.damage_grade),
                    "grade_raw": a.damage_grade,
                    "area_km2": a.affected_area_km2,
                    "url": a.download_url,
                },
                timestamp=a.timestamp,
            )
        )
    return rows


async def replace_assessments(
    session: AsyncSession, event_id: UUID, activation: str, assessments: list[DamageAssessment]
) -> int:
    """Swap the event's layers for this activation with the latest set."""
    await session.execute(
        delete(GeoLayer).where(
            GeoLayer.event_id == event_id,
            GeoLayer.layer_type == LAYER_TYPE,
            GeoLayer.properties["activation"].astext == activation,
        )
    )
    rows = to_layers(event_id, assessments)
    session.add_all(rows)
    await session.flush()
    return len(rows)


async def sync_damage(
    session: AsyncSession, service: CopernicusEMSService, limit: int = MAX_EVENTS_PER_RUN
) -> dict[str, int]:
    """Refresh damage layers for active events that have a Copernicus activation."""
    rows = (
        await session.execute(
            select(Event.id, EventSource.external_id)
            .join(EventSource, EventSource.event_id == Event.id)
            .join(DataSource, DataSource.id == EventSource.source_id)
            .where(DataSource.name == "Copernicus", Event.is_active.is_(True), Event.is_canonical.is_(True))
            .order_by(Event.start_date.desc())
            .limit(limit)
        )
    ).all()
    events = stored = 0
    for event_id, activation in rows:
        if not activation:
            continue
        assessments = await service.fetch_damage_assessments(activation)
        if assessments:
            stored += await replace_assessments(session, event_id, activation, assessments)
        events += 1
        await asyncio.sleep(REQUEST_GAP_SECONDS)
    return {"events": events, "assessments": stored}


# --- read side -------------------------------------------------------------


class DamageArea(BaseModel):
    id: UUID
    name: str | None
    grade: Grade
    product_type: str | None
    area_km2: float | None
    url: str | None
    activation: str | None
    timestamp: datetime | None
    geometry: dict[str, Any]


class DamageSummary(BaseModel):
    """What the event's damage assessments add up to."""

    event_id: UUID
    total: int
    by_grade: dict[str, int]
    area_km2_by_grade: dict[str, float]
    activations: list[str]
    updated_at: datetime | None
    areas: list[DamageArea]


def summarize(event_id: UUID, layers: list[GeoLayer]) -> DamageSummary:
    by_grade = {g: 0 for g in GRADES}
    area = {g: 0.0 for g in GRADES}
    areas: list[DamageArea] = []
    activations: set[str] = set()
    updated: datetime | None = None
    for layer in layers:
        p = layer.properties or {}
        grade: Grade = p.get("grade") if p.get("grade") in GRADES else "unknown"
        by_grade[grade] += 1
        if isinstance(p.get("area_km2"), (int, float)):
            area[grade] += float(p["area_km2"])
        if p.get("activation"):
            activations.add(str(p["activation"]))
        ts = layer.timestamp
        if ts and (updated is None or ts > updated):
            updated = ts
        areas.append(
            DamageArea(
                id=layer.id,
                name=p.get("name"),
                grade=grade,
                product_type=p.get("product_type"),
                area_km2=p.get("area_km2"),
                url=p.get("url") if isinstance(p.get("url"), str) and str(p.get("url")).startswith("https://") else None,
                activation=p.get("activation"),
                timestamp=ts,
                geometry=layer.geojson,
            )
        )
    # Worst first, so lists and legends lead with what matters
    areas.sort(key=lambda a: GRADES.index(a.grade))
    return DamageSummary(
        event_id=event_id,
        total=len(layers),
        by_grade=by_grade,
        area_km2_by_grade={g: round(v, 2) for g, v in area.items()},
        activations=sorted(activations),
        updated_at=updated,
        areas=areas,
    )


async def damage_for_event(session: AsyncSession, event_id: UUID) -> DamageSummary:
    layers = (
        await session.scalars(
            select(GeoLayer)
            .where(GeoLayer.event_id == event_id, GeoLayer.layer_type == LAYER_TYPE)
            .limit(2000)
        )
    ).all()
    return summarize(event_id, list(layers))

