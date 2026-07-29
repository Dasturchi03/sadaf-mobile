from fastapi import Security, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from sqlalchemy import select

from app.api.auth.models.users import Users
from app.services.common import db_common as db


users_t = Users.__table__


class BasicAuthHandler:
    security = HTTPBasic()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    async def auth_wrapper(self, credentials: HTTPBasicCredentials = Security(security)):
        user = await db.orm_one(
            select(users_t.c.id, users_t.c.username, users_t.c.password_hash).where(
                users_t.c.username == credentials.username,
                users_t.c.is_active.is_(True),
            )
        )
        if not user:
            raise HTTPException(status_code=403, detail='Not authenticated!')

        if not self.verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid password!")

        return True
