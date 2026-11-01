"""Site plan requests and responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.models.plan import PlanVisibility

# Kinds by index, as the web planner encodes them
PLAN_KINDS = ("tent", "tap", "toilet", "health", "distribution")
MAX_ITEMS = 20_000

PlanItems = list[tuple[int, float, float]]


def _check_items(items: PlanItems) -> PlanItems:
    for kind, lat, lng in items:
        if not 0 <= kind < len(PLAN_KINDS):
            raise ValueError("Unknown item kind")
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError("Item coordinates out of range")
    return items


class PlanContent(BaseModel):
    population: int = Field(ge=0, le=1_000_000)
    items: PlanItems = Field(max_length=MAX_ITEMS)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("items")
    @classmethod
    def valid_items(cls, v: PlanItems) -> PlanItems:
        return _check_items(v)


class PlanCreate(PlanContent):
    title: str = Field(min_length=3, max_length=200)
    event_id: UUID | None = None
    visibility: PlanVisibility = PlanVisibility.public


class PlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    visibility: PlanVisibility | None = None


class PlanFork(BaseModel):
    version: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=3, max_length=200)


class PlanVersionMeta(BaseModel):
    number: int
    population: int
    item_count: int
    note: str | None
    created_at: datetime


class PlanSummary(BaseModel):
    id: UUID
    title: str
    event_id: UUID | None
    visibility: PlanVisibility
    latest_version: int
    population: int
    item_count: int
    forked_from_id: UUID | None
    is_mine: bool
    updated_at: datetime


class PlanOut(PlanSummary):
    forked_from_version: int | None
    version: int
    items: PlanItems
    note: str | None
    versions: list[PlanVersionMeta]
    created_at: datetime


class PlanList(BaseModel):
    data: list[PlanSummary]
