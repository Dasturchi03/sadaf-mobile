from __future__ import annotations

from sqlalchemy import insert, select

from app.api.auth.models.users import Users
from app.services.common import db_common as db
from app.utils.exc import NotFoundError


users_t = Users.__table__


async def _get_user(user_id: int | None = None, username: str | None = None):
    if user_id is not None:
        user = await db.orm_one(
            select(users_t).where(users_t.c.id == user_id, users_t.c.is_active.is_(True))
        )
    elif username is not None:
        user = await db.orm_one(
            select(users_t).where(users_t.c.username == username, users_t.c.is_active.is_(True))
        )
    else:
        user = None

    if not user:
        raise NotFoundError(404, "User not found!")

    return user


async def _get_users():
    return await db.orm_all(
        select(
            users_t.c.id,
            users_t.c.username,
            users_t.c.phone_number,
            users_t.c.crm_user_id,
            users_t.c.crm_client_id,
            users_t.c.first_name,
            users_t.c.last_name,
            users_t.c.is_active,
            users_t.c.is_verified,
            users_t.c.created_at,
        ).order_by(users_t.c.id.desc())
    )


async def _create_user(username: str, password_hash: str):
    return await db.orm_one(
        insert(users_t)
        .values(username=username, password_hash=password_hash, is_verified=True)
        .returning(
            users_t.c.id,
            users_t.c.username,
            users_t.c.phone_number,
            users_t.c.crm_user_id,
            users_t.c.crm_client_id,
            users_t.c.first_name,
            users_t.c.last_name,
            users_t.c.is_active,
            users_t.c.is_verified,
            users_t.c.created_at,
        )
    )
