from fastapi.exceptions import HTTPException
from sqlalchemy import func, select, update

from app.api.auth.models.users import Users
from app.api.auth.schemas import user_auth as sc
from app.models.mobile import RefreshToken
from app.services.common import db_common as db
from app.services.users import users
from app.utils.deps.auth import auth_handler


users_t = Users.__table__
refresh_tokens_t = RefreshToken.__table__


def _auth_payload(user: dict, access: str, refresh: str) -> dict:
    return {
        "refresh": refresh,
        "access": access,
        "user_id": user["id"],
        "client_id": user.get("crm_client_id"),
        "username": user.get("username"),
        "user_fullname": " ".join(
            part for part in [user.get("first_name"), user.get("last_name")] if part
        ),
    }


async def login_user(request: sc.UserLoginRequest):
    user = await users.get_user(username=request.username)
    if user and auth_handler.verify_password(request.password, user.get("password_hash")):
        access = auth_handler.encode_token(user)
        refresh, _ = await auth_handler.issue_refresh_token(user["id"])
        return _auth_payload(user, access, refresh)
    raise HTTPException(401, "Parol noto'g'ri")


async def refresh_token(request: sc.TokenRefreshRequest):
    refresh = request.refresh.strip()
    if not refresh:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    token_hash = auth_handler.hash_refresh_token(refresh)
    row = await db.orm_one(
        select(
            refresh_tokens_t.c.id.label("refresh_token_id"),
            users_t.c.id,
            users_t.c.username,
            users_t.c.phone_number,
            users_t.c.crm_user_id,
            users_t.c.crm_client_id,
            users_t.c.first_name,
            users_t.c.last_name,
            users_t.c.father_name,
            users_t.c.birthdate,
            users_t.c.gender,
            users_t.c.citizenship,
            users_t.c.address,
            users_t.c.telegram,
            users_t.c.is_active,
            users_t.c.is_verified,
        )
        .select_from(refresh_tokens_t.join(users_t, users_t.c.id == refresh_tokens_t.c.user_id))
        .where(
            refresh_tokens_t.c.token_hash == token_hash,
            refresh_tokens_t.c.revoked_at.is_(None),
            refresh_tokens_t.c.expires_at > func.now(),
            users_t.c.is_active.is_(True),
        )
        .limit(1)
    )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    await db.orm_execute(
        update(refresh_tokens_t)
        .where(refresh_tokens_t.c.id == row["refresh_token_id"])
        .values(revoked_at=func.now())
    )
    user = {key: value for key, value in row.items() if key != "refresh_token_id"}
    access = auth_handler.encode_token(user)
    new_refresh, _ = await auth_handler.issue_refresh_token(user["id"])
    return _auth_payload(user, access, new_refresh)
