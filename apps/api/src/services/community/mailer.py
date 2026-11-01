"""Outgoing mail: SMTP when configured, otherwise the log (development)."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from src.core.config import Settings

logger = logging.getLogger(__name__)


class Mailer(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...


class LogMailer:
    """Writes mail to the log. For development; never for production."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))
        logger.info("Mail (not sent, no SMTP_HOST) to=%s subject=%s\n%s", to, subject, body)


class SmtpMailer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _send_sync(self, msg: EmailMessage) -> None:
        s = self.settings
        assert s.smtp_host
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            if s.smtp_starttls:
                smtp.starttls()
            if s.smtp_user and s.smtp_password:
                smtp.login(s.smtp_user, s.smtp_password.get_secret_value())
            smtp.send_message(msg)

    async def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        await asyncio.to_thread(self._send_sync, msg)


_log_mailer = LogMailer()


def mailer_for(settings: Settings) -> Mailer:
    return SmtpMailer(settings) if settings.smtp_host else _log_mailer
