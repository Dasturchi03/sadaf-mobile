from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.mobile import schemas as sc
from app.api.auth.models.users import Users
from app.core.config import settings
from app.models.mobile import Notification, NotificationDevice
from app.services.common import db_common as db
from app.services.mobile import demo_account, push
from app.services.mobile.common import offset_limit, paginate_rows
from app.utils.i18n import localized


notifications_t = Notification.__table__
devices_t = NotificationDevice.__table__
users_t = Users.__table__


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


def _push_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") or {}
    data = {
        "notification_id": row["notification_id"],
        "notification_type": row["notification_type"],
        "next_action": "open_reservation" if row.get("crm_reservation_id") else "open_notifications",
        "target_type": "reservation" if row.get("crm_reservation_id") else "notification",
        "target_id": row.get("crm_reservation_id") or row["notification_id"],
    }
    if row.get("crm_reservation_id"):
        data["reservation_id"] = row["crm_reservation_id"]
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key != "reservation":
                data[key] = value
    return data


async def create_notification(
    *,
    user_id: int,
    notification_type: str = "general",
    message: str | None = None,
    crm_notification_id: int | None = None,
    crm_reservation_id: int | None = None,
    payload: dict[str, Any] | None = None,
    send_push: bool = True,
    include_push_result: bool = False,
) -> dict[str, Any]:
    row = await db.orm_one(
        pg_insert(notifications_t)
        .values(
            user_id=user_id,
            crm_notification_id=crm_notification_id,
            crm_reservation_id=crm_reservation_id,
            notification_type=notification_type,
            notification_message=message,
            payload=payload or {},
        )
        .returning(notifications_t)
    )
    if not row:
        raise HTTPException(status_code=500, detail="Notification creation failed")

    serialized = _serialize(dict(row))
    sent_count = 0
    if send_push:
        title = serialized["status_label"]
        body = serialized["notification_message"] or title
        sent_count = await push.send_push_to_user(
            user_id=user_id,
            title=title,
            body=body,
            data=_push_payload(dict(row)),
        )
    if include_push_result:
        serialized["push_sent_count"] = sent_count
    return serialized


async def test_send_notification(
    auth_user: dict[str, Any],
    request: sc.MobileNotificationTestSendRequest,
) -> dict[str, Any]:
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    user = await db.orm_one(
        select(users_t.c.id, users_t.c.username)
        .where(
            users_t.c.username == request.username,
            users_t.c.is_active.is_(True),
        )
        .limit(1)
    )
    if not user:
        raise HTTPException(status_code=404, detail="User was not found")

    result = await create_notification(
        user_id=user["id"],
        notification_type="general",
        message=request.message,
        payload={
            "source": "test_api",
            "target_username": request.username,
            "requested_by_user_id": auth_user["id"],
            "requested_by_username": auth_user.get("username"),
        },
        include_push_result=True,
    )
    result["target_user_id"] = user["id"]
    result["target_username"] = user["username"]
    return result


async def list_notifications(auth_user: dict[str, Any], *, page: int | None, page_size: int | None):
    if demo_account.is_demo_auth(auth_user):
        return demo_account.paginated_section("notifications", page=page, page_size=page_size)

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
    if demo_account.is_demo_auth(auth_user):
        for row in demo_account.section("notifications", []):
            if row.get("notification_id") == notification_id:
                row["is_read"] = True
                return row
        raise HTTPException(status_code=404, detail="Notification was not found")

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
    if demo_account.is_demo_auth(auth_user):
        return {"updated_count": len([row for row in demo_account.section("notifications", []) if not row.get("is_read")])}

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
