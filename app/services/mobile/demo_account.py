from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.auth.models.users import Users
from app.core.config import settings
from app.services.common import db_common as db
from app.services.mobile.common import paginate_rows


users_t = Users.__table__


def _data_path() -> Path:
    path = Path(settings.DEMO_ACCOUNT_DATA_FILE)
    if path.is_absolute():
        return path
    return Path.cwd() / path


def data() -> dict[str, Any]:
    path = _data_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def enabled() -> bool:
    return bool(settings.DEMO_ACCOUNT_ENABLED and settings.DEMO_ACCOUNT_PHONE)


def is_demo_phone(phone_number: str | None) -> bool:
    if not enabled() or not phone_number:
        return False
    return phone_number.strip() == str(settings.DEMO_ACCOUNT_PHONE).strip()


def is_demo_auth(auth_user: dict[str, Any] | None) -> bool:
    if not auth_user:
        return False
    return is_demo_phone(auth_user.get("phone_number") or auth_user.get("username"))


def is_demo_user(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    return is_demo_phone(user.get("phone_number") or user.get("username"))


async def ensure_user(phone_number: str) -> dict[str, Any]:
    fixture = data().get("profile", {})
    birthdate = fixture.get("client_birthdate")
    if isinstance(birthdate, str):
        birthdate = date.fromisoformat(birthdate)
    stmt = pg_insert(users_t).values(
        username=phone_number,
        phone_number=phone_number,
        crm_client_id=None,
        first_name=fixture.get("client_firstname") or "Demo",
        last_name=fixture.get("client_lastname") or "Patient",
        father_name=fixture.get("client_father_name"),
        birthdate=birthdate,
        gender=fixture.get("client_gender"),
        citizenship=fixture.get("client_citizenship") or "UZ",
        address=fixture.get("client_address"),
        telegram=fixture.get("client_telegram"),
        is_active=True,
        is_verified=True,
    )
    excluded = stmt.excluded
    return await db.orm_one(
        stmt.on_conflict_do_update(
            index_elements=[users_t.c.phone_number],
            set_={
                "username": excluded.username,
                "crm_client_id": None,
                "first_name": excluded.first_name,
                "last_name": excluded.last_name,
                "father_name": excluded.father_name,
                "birthdate": excluded.birthdate,
                "gender": excluded.gender,
                "citizenship": excluded.citizenship,
                "address": excluded.address,
                "telegram": excluded.telegram,
                "is_active": True,
                "is_verified": True,
                "updated_at": func.now(),
            },
        ).returning(users_t)
    )


async def touch_login(user_id: int) -> None:
    await db.orm_execute(
        update(users_t)
        .where(users_t.c.id == user_id)
        .values(last_login_at=func.now(), updated_at=func.now())
    )


async def user_by_phone(phone_number: str) -> dict[str, Any] | None:
    return await db.orm_one(select(users_t).where(users_t.c.phone_number == phone_number))


def profile(user: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(data().get("profile", {}))
    payload.update(
        {
            "client_id": user["id"],
            "username": user.get("username"),
            "phone": user.get("phone_number"),
        }
    )
    payload.setdefault(
        "full_name",
        " ".join(
            part for part in [payload.get("client_firstname"), payload.get("client_lastname")] if part
        ),
    )
    return payload


def section(name: str, default: Any):
    return deepcopy(data().get(name, default))


def paginated_section(name: str, *, page: int | None, page_size: int | None):
    rows = section(name, [])
    if page:
        safe_size = max(page_size or 10, 1)
        start = (max(page, 1) - 1) * safe_size
        rows = rows[start : start + safe_size]
    return paginate_rows(rows, count=len(section(name, [])), page=page, page_size=page_size)
