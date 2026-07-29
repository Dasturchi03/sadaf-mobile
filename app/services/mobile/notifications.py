from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.mobile import schemas as sc
from app.models.mobile import Notification, NotificationDevice
from app.services.common import db_common as db
from app.services.mobile.common import offset_limit, paginate_rows
from app.utils.i18n import localized


notifications_t = Notification.__table__
devices_t = NotificationDevice.__table__


TYPE_LABELS = {
    "general": {"uz": "Bildirishnoma", "ru": "Уведомление", "en": "Notification"},
    "reservation": {"uz": "Qabul", "ru": "Запись", "en": "Reservation"},
    "reservation_request": {
        "uz": "Qabul so'rovi",
        "ru": "Заявка на запись",
        "en": "Reservation request",
    },
    "cashback": {"uz": "Cashback", "ru": "Кэшбек", "en": "Cashback"},
}


def _json_value(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") or {}
    reservation_payload = payload.get("reservation") if isinstance(payload, dict) else None
    return {
        "notification_id": row["notification_id"],
        "notification_type": row["notification_type"],
        "notification_message": row.get("notification_message"),
        "notification_reservation": reservation_payload,
        "is_read": row["is_read"],
        "status_label": (
            localized(TYPE_LABELS[row["notification_type"]], row["notification_type"])
            if row["notification_type"] in TYPE_LABELS
            else row["notification_type"]
        ),
        "next_action": "open_reservation" if row.get("crm_reservation_id") else "open_notifications",
        "payload": {key: _json_value(value) for key, value in payload.items()} if isinstance(payload, dict) else payload,
        "created_at": _json_value(row["created_at"]),
    }


async def list_notifications(auth_user: dict[str, Any], *, page: int | None, page_size: int | None):
    offset, limit = offset_limit(page, page_size)
    count = await db.orm_scalar(
        select(func.count())
        .select_from(notifications_t)
        .where(notifications_t.c.user_id == auth_user["id"])
    )
    stmt = (
        select(notifications_t)
        .where(notifications_t.c.user_id == auth_user["id"])
        .order_by(notifications_t.c.created_at.desc())
    )
    if page:
        stmt = stmt.offset(offset).limit(limit)
    rows = await db.orm_all(stmt)
    data = [_serialize(dict(row)) for row in rows]
    return paginate_rows(data, count=count, page=page, page_size=page_size)


async def read_notification(auth_user: dict[str, Any], notification_id: int):
    row = await db.orm_one(
        update(notifications_t)
        .where(
            notifications_t.c.notification_id == notification_id,
            notifications_t.c.user_id == auth_user["id"],
        )
        .values(is_read=True)
        .returning(notifications_t)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification was not found")
    return _serialize(dict(row))


async def read_all(auth_user: dict[str, Any]):
    result = await db.orm_execute(
        update(notifications_t)
        .where(
            notifications_t.c.user_id == auth_user["id"],
            notifications_t.c.is_read.is_(False),
        )
        .values(is_read=True)
    )
    return {"updated_count": result.rowcount or 0}


async def register_device(auth_user: dict[str, Any], request: sc.MobileNotificationDeviceRequest):
    stmt = pg_insert(devices_t).values(
        user_id=auth_user["id"],
        token=request.token,
        platform=request.platform,
        device_uid=request.device_uid,
        is_active=True,
        last_seen_at=func.now(),
    )
    row = await db.orm_one(
        stmt.on_conflict_do_update(
            index_elements=[devices_t.c.token],
            set_={
                "user_id": stmt.excluded.user_id,
                "platform": stmt.excluded.platform,
                "device_uid": stmt.excluded.device_uid,
                "is_active": True,
                "last_seen_at": func.now(),
            },
        ).returning(
            devices_t.c.device_id,
            devices_t.c.token,
            devices_t.c.platform,
            devices_t.c.device_uid,
            devices_t.c.is_active,
            devices_t.c.last_seen_at,
        )
    )
    return {key: _json_value(value) for key, value in dict(row).items()}
