from fastapi.exceptions import HTTPException

from app.api.auth.schemas import user_auth as sc
from app.services.users import users
from app.utils.deps.auth import auth_handler


async def login_user(request: sc.UserLoginRequest):
    user = await users.get_user(username=request.username)
    if user and auth_handler.verify_password(request.password, user.get("password_hash")):
        access = auth_handler.encode_token(user)
        refresh, _ = auth_handler.encode_refresh_token(user["id"])
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
    raise HTTPException(401, "Parol noto'g'ri")
