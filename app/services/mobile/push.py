from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.models.mobile import NotificationDevice
from app.services.common import db_common as db


logger = logging.getLogger(__name__)

devices_t = NotificationDevice.__table__


def _firebase_app():
    credentials_file = settings.FIREBASE_CREDENTIALS_FILE
    if not credentials_file:
        logger.info("Firebase credentials file is not configured")
        return None
    if not Path(credentials_file).exists():
        logger.warning("Firebase credentials file does not exist: %s", credentials_file)
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning("firebase-admin is not installed, push notification was skipped")
        return None

    try:
        return firebase_admin.get_app()
    except ValueError:
        return firebase_admin.initialize_app(credentials.Certificate(credentials_file))


def _send_one(token: str, title: str, body: str, data: dict[str, str]) -> bool:
    app = _firebase_app()
    if app is None:
        return False

    from firebase_admin import messaging

    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data=data,
    )
    messaging.send(message, app=app)
    return True


def _stringify_payload(payload: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in payload.items()
        if value is not None
    }


async def send_push_to_user(
    *,
    user_id: int,
    title: str,
    body: str,
    data: dict[str, Any],
) -> int:
    rows = await db.orm_all(
        select(devices_t.c.token).where(
            devices_t.c.user_id == user_id,
            devices_t.c.is_active.is_(True),
        )
    )
    tokens = [row["token"] for row in rows if row.get("token")]
    if not tokens:
        return 0

    string_data = _stringify_payload(data)
    sent_count = 0
    for token in tokens:
        try:
            sent = await asyncio.to_thread(_send_one, token, title, body, string_data)
            if sent:
                sent_count += 1
        except Exception:
            logger.exception("Failed to send Firebase notification to user_id=%s", user_id)
    return sent_count
