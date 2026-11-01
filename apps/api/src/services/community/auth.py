"""Passwordless login by emailed one-time link, and sessions.

Tokens are random 256-bit values. Only their SHA-256 is stored, so a leaked
database does not let anyone log in. A link works once and expires after
MAGIC_LINK_TTL_MINUTES; sessions expire after SESSION_TTL_DAYS and can be
revoked by logging out.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.models.community import MagicLinkToken, User, UserSession
from src.services.community.mailer import Mailer

# Deliberately simple: one @, no spaces, a dot in the domain. Delivery is the
# real check — the link only works if the mail arrives.
_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")


class InvalidEmail(ValueError):
    pass


def normalize_email(email: str) -> str:
    e = email.strip().lower()
    if len(e) > 320 or not _EMAIL_RE.match(e):
        raise InvalidEmail("Enter a valid email address")
    return e


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def safe_redirect(path: str | None) -> str:
    """Only same-site paths: '/x' yes, '//evil.com' or 'https://…' no."""
    if not path or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/"
    return path[:300]


@dataclass
class LoginResult:
    session_token: str
    user: User
    redirect_path: str


async def request_login_link(
    session: AsyncSession,
    email: str,
    redirect_path: str | None,
    settings: Settings,
    mailer: Mailer,
    now: datetime | None = None,
) -> str | None:
    """Create and mail a login link. Returns the raw token, or None if rate-limited.

    The caller must answer the same way in both cases so the endpoint does
    not reveal anything about the address.
    """
    now = now or datetime.now(UTC)
    address = normalize_email(email)
    recent = await session.scalar(
        select(func.count())
        .select_from(MagicLinkToken)
        .where(MagicLinkToken.email == address, MagicLinkToken.created_at > now - timedelta(hours=1))
    )
    if (recent or 0) >= settings.magic_link_max_per_hour:
        return None

    token = secrets.token_urlsafe(32)
    session.add(
        MagicLinkToken(
            email=address,
            token_hash=hash_token(token),
            redirect_path=safe_redirect(redirect_path),
            created_at=now,
            expires_at=now + timedelta(minutes=settings.magic_link_ttl_minutes),
        )
    )
    await session.flush()
    link = f"{settings.public_web_url.rstrip('/')}/login/verify?{urlencode({'token': token})}"
    await mailer.send(
        address,
        "Your Phoenix sign-in link",
        "Use this link to sign in to Phoenix. It works once and expires in "
        f"{settings.magic_link_ttl_minutes} minutes.\n\n{link}\n\n"
        "If you did not ask to sign in, ignore this message.",
    )
    return token


async def verify_login_link(
    session: AsyncSession, token: str, settings: Settings, now: datetime | None = None
) -> LoginResult | None:
    """Consume a link (atomically, once) and open a session. None if invalid."""
    now = now or datetime.now(UTC)
    row = (
        await session.execute(
            update(MagicLinkToken)
            .where(
                MagicLinkToken.token_hash == hash_token(token),
                MagicLinkToken.used_at.is_(None),
                MagicLinkToken.expires_at > now,
            )
            .values(used_at=now)
            .returning(MagicLinkToken.email, MagicLinkToken.redirect_path)
        )
    ).first()
    if row is None:
        return None
    email, redirect = row

    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, created_at=now)
        session.add(user)
    user.last_login_at = now
    await session.flush()

    raw = secrets.token_urlsafe(32)
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(raw),
            created_at=now,
            expires_at=now + timedelta(days=settings.session_ttl_days),
        )
    )
    await session.flush()
    return LoginResult(session_token=raw, user=user, redirect_path=safe_redirect(redirect))


async def user_for_session(session: AsyncSession, token: str, now: datetime | None = None) -> User | None:
    now = now or datetime.now(UTC)
    return await session.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            UserSession.token_hash == hash_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )


async def revoke_session(session: AsyncSession, token: str, now: datetime | None = None) -> None:
    await session.execute(
        update(UserSession)
        .where(UserSession.token_hash == hash_token(token), UserSession.revoked_at.is_(None))
        .values(revoked_at=now or datetime.now(UTC))
    )


def is_platform_admin(user: User, settings: Settings) -> bool:
    return user.email in {e.strip().lower() for e in settings.platform_admin_emails}
