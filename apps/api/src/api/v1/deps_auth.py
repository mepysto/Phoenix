"""Who is calling: session cookie (browser) or Bearer token (API clients)."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.db.database import get_db
from src.models.community import User
from src.services.community.auth import user_for_session
from src.services.community.mailer import Mailer, mailer_for
from src.services.community.service import CommunityService, Viewer


def get_mailer() -> Mailer:
    return mailer_for(get_settings())


def session_token(request: Request, settings: Settings = Depends(get_settings)) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.cookies.get(settings.session_cookie_name)


async def optional_user(
    token: Annotated[str | None, Depends(session_token)],
    session: AsyncSession = Depends(get_db),
) -> User | None:
    if not token:
        return None
    return await user_for_session(session, token)


async def required_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return user


def get_community_service(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    mailer: Mailer = Depends(get_mailer),
) -> CommunityService:
    return CommunityService(session, settings, mailer)


async def viewer(
    user: Annotated[User | None, Depends(optional_user)],
    service: Annotated[CommunityService, Depends(get_community_service)],
) -> Viewer:
    return await service.viewer(user)


async def signed_in_viewer(
    user: Annotated[User, Depends(required_user)],
    service: Annotated[CommunityService, Depends(get_community_service)],
) -> Viewer:
    return await service.viewer(user)
