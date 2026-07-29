from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


if TYPE_CHECKING:
    from app.models import *


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        Index("users_crm_client_id_idx", "crm_client_id"),
        Index("users_phone_number_idx", "phone_number"),
        {'comment': 'Пользователи'},
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(150), unique=True, comment="Имя пользователя")
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), comment="Пароль")
    crm_user_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    crm_client_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    first_name: Mapped[str | None] = mapped_column(String(80))
    last_name: Mapped[str | None] = mapped_column(String(80))
    father_name: Mapped[str | None] = mapped_column(String(80))
    birthdate: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))
    citizenship: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(255))
    telegram: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __str__(self):
        return f'{self.id}. {self.username}'
