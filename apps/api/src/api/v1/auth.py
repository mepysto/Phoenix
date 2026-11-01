"""Sign in with an emailed link; no passwords."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.deps_auth import (
    get_community_service,
    get_mailer,
    session_token,
    signed_in_viewer,
)
from src.core.config import Settings, get_settings
from src.db.database import get_db
from src.schemas.community import LoginLinkRequest, LoginLinkResponse, Me, MeUpdate, SessionResponse, VerifyRequest
from src.services.community.auth import (
    InvalidEmail,
    request_login_link,
    revoke_session,
    verify_login_link,
)
from src.services.community.mailer import Mailer
from src.services.community.service import CommunityService, Viewer

router = APIRouter()


@router.post("/login-link", response_model=LoginLinkResponse, status_code=202)
async def login_link(
    body: LoginLinkRequest,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    mailer: Mailer = Depends(get_mailer),
) -> LoginLinkResponse:
    """Email a one-time sign-in link. Answers the same whether or not the address is known."""
    try:
        token = await request_login_link(session, body.email, body.redirect_path, settings, mailer)
    except InvalidEmail as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    dev = settings.auth_dev_return_link and settings.environment != "production"
    link = f"{settings.public_web_url.rstrip('/')}/login/verify?token={token}" if dev and token else None
    return LoginLinkResponse(sent=True, dev_link=link)


@router.post("/verify", response_model=SessionResponse)
async def verify(
    body: VerifyRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    service: CommunityService = Depends(get_community_service),
) -> SessionResponse:
    """Exchange a sign-in link for a session (HttpOnly cookie)."""
    result = await verify_login_link(session, body.token, settings)
    if result is None:
        raise HTTPException(status_code=400, detail="This sign-in link is invalid or has expired")
    response.set_cookie(
        settings.session_cookie_name,
        result.session_token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    viewer = await service.viewer(result.user)
    return SessionResponse(user=service.me(viewer), redirect_path=result.redirect_path)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    token: Annotated[str | None, Depends(session_token)],
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    if token:
        await revoke_session(session, token)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=Me)
async def me(
    viewer: Annotated[Viewer, Depends(signed_in_viewer)],
    service: CommunityService = Depends(get_community_service),
) -> Me:
    return service.me(viewer)


@router.patch("/me", response_model=Me)
async def update_me(
    body: MeUpdate,
    viewer: Annotated[Viewer, Depends(signed_in_viewer)],
    service: CommunityService = Depends(get_community_service),
) -> Me:
    assert viewer.user is not None
    viewer.user.display_name = (body.display_name or "").strip() or None
    return service.me(viewer)
