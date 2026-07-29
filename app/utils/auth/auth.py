from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select

from app.api.auth.models.users import Users
from app.core.security import security as app_security
from app.services.common import db_common as db


users_t = Users.__table__


class AuthHandler:
    security = HTTPBearer()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    secret = app_security.AUTH_SECRET_KEY
    access_lifetime = timedelta(hours=12)

    @classmethod
    def get_password_hash(cls, password: str) -> str:
        return cls.pwd_context.hash(password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str | None) -> bool:
        if not hashed_password:
            return False
        return cls.pwd_context.verify(plain_password, hashed_password)

    def encode_token(self, user: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "iat": now,
            "exp": now + self.access_lifetime,
            "user_id": user["id"],
            "username": user.get("username"),
            "crm_client_id": user.get("crm_client_id"),
            "crm_user_id": user.get("crm_user_id"),
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    async def decode_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail={"status": "Signature has expired"})
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail={"status": "Invalid token"})

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=403, detail="Not authenticated!")

        user = await db.orm_one(
            select(
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
            ).where(users_t.c.id == int(user_id), users_t.c.is_active.is_(True))
        )
        if user is None:
            raise HTTPException(status_code=403, detail="Not authenticated!")
        return user

    async def auth_wrapper(
        self,
        auth: HTTPAuthorizationCredentials = Security(security),
    ) -> dict[str, Any]:
        return await self.decode_token(auth.credentials)

    def encode_refresh_token(self, user_id: int):
        token = secrets.token_hex(32)
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        return token, expires

    def decode_access_token(self, token: str):
        return jwt.decode(token, self.secret, algorithms=["HS256"])
