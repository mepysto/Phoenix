"""Closed-tab area alerts: Web Push subscriptions (opt-in, no account)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.db.database import get_db
from src.models.push import PushSubscription
from src.services.push.alerts import is_push_endpoint
from src.services.push.webpush import VapidKeys, b64u_decode

router = APIRouter()


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=80, max_length=120)
    auth: str = Field(min_length=16, max_length=40)

    @field_validator("p256dh", "auth")
    @classmethod
    def base64url(cls, v: str) -> str:
        try:
            b64u_decode(v)
        except Exception as exc:
            raise ValueError("Not base64url") from exc
        return v


class PushArea(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_km: int = Field(ge=10, le=1000)
    min_severity: Literal["low", "medium", "high", "critical"] = "high"


class SubscriptionIn(BaseModel):
    endpoint: str = Field(max_length=1000)
    keys: PushKeys
    areas: list[PushArea] = Field(min_length=1, max_length=10)
    lang: str = Field(default="en", max_length=5)

    @field_validator("endpoint")
    @classmethod
    def known_push_service(cls, v: str) -> str:
        if not is_push_endpoint(v):
            raise ValueError("Not a supported push service endpoint")
        return v


class Unsubscribe(BaseModel):
    endpoint: str = Field(max_length=1000)


class VapidKey(BaseModel):
    public_key: str


def _keys(settings: Settings) -> VapidKeys:
    if settings.vapid_private_key is None:
        raise HTTPException(status_code=503, detail="Closed-tab alerts are not set up on this server")
    return VapidKeys.from_private(settings.vapid_private_key.get_secret_value())


@router.get("/vapid-public-key", response_model=VapidKey)
async def vapid_public_key(settings: Settings = Depends(get_settings)) -> VapidKey:
    return VapidKey(public_key=_keys(settings).public_b64u)


@router.put("/subscription", status_code=204)
async def subscribe(
    body: SubscriptionIn,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """Create or update this browser's subscription and its areas."""
    _keys(settings)
    # Areas are places, not people: keep ~10 km precision only
    areas = [{**a.model_dump(), "lat": round(a.lat, 1), "lng": round(a.lng, 1)} for a in body.areas]
    sub = await session.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub is None:
        session.add(
            PushSubscription(
                endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth, areas=areas, lang=body.lang
            )
        )
    else:
        sub.p256dh, sub.auth, sub.areas, sub.lang, sub.failures = body.keys.p256dh, body.keys.auth, areas, body.lang, 0
    await session.flush()


@router.post("/unsubscribe", status_code=204)
async def unsubscribe(body: Unsubscribe, session: AsyncSession = Depends(get_db)) -> None:
    """Delete this browser's subscription and its areas."""
    await session.execute(delete(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
