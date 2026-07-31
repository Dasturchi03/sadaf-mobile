from __future__ import annotations

import re
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from asyncpg.exceptions import UndefinedColumnError, UndefinedTableError
from fastapi import HTTPException
from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.mobile import schemas as sc
from app.api.auth.models.users import Users
from app.core.config import settings
from app.models.mobile import (
    CashbackEntry,
    MobileEvent,
    OTPCode,
    ReferralApplication,
    ReferralCode,
    ReservationRequest,
    Notification,
    UserContact,
)
from app.services.common import db_common as db
from app.services.mobile import sms
from app.utils.deps.auth import auth_handler
from app.utils.di.db_ctx import CRM_DB


users_t = Users.__table__
otp_t = OTPCode.__table__
events_t = MobileEvent.__table__
referral_codes_t = ReferralCode.__table__
referral_applications_t = ReferralApplication.__table__
cashback_entries_t = CashbackEntry.__table__
reservation_requests_t = ReservationRequest.__table__
notifications_t = Notification.__table__
user_contacts_t = UserContact.__table__


TIER_THRESHOLDS = {
    "bronze": Decimal("0"),
    "silver": Decimal("5000000"),
    "gold": Decimal("15000000"),
}
TIER_REFERRAL_REQUIREMENTS = {
    "bronze": 0,
    "silver": 3,
    "gold": 10,
}
TIER_CASHBACK_RATES = {
    "bronze": Decimal("0.03"),
    "silver": Decimal("0.05"),
    "gold": Decimal("0.07"),
}
TIER_LABELS = {
    "bronze": "Bronze",
    "silver": "Silver",
    "gold": "Gold",
}


def _json_value(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _normalize_phone(phone_number: str) -> str:
    phone = phone_number.strip()
    if not re.match(settings.PHONE_PATTERN, phone):
        raise HTTPException(
            status_code=400,
            detail={"phone_number": "Phone number pattern example: +998901234567"},
        )
    return phone


def _full_name(row: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in [
            row.get("first_name") or row.get("client_firstname"),
            row.get("last_name") or row.get("client_lastname"),
        ]
        if part
    ).strip()


def _next_tier(tier: str | None) -> str | None:
    if tier == "bronze" or not tier:
        return "silver"
    if tier == "silver":
        return "gold"
    return None


def _cashback_percent(tier: str | None) -> float:
    rate = TIER_CASHBACK_RATES.get(tier or "bronze", TIER_CASHBACK_RATES["bronze"])
    return float(rate * 100)


def _tier_from_spent(total_spent: Decimal | float | int | None) -> str:
    amount = Decimal(str(total_spent or 0))
    if amount >= TIER_THRESHOLDS["gold"]:
        return "gold"
    if amount >= TIER_THRESHOLDS["silver"]:
        return "silver"
    return "bronze"


async def _get_crm_client_by_phone(phone_number: str) -> dict[str, Any] | None:
    try:
        row = await CRM_DB.fetchrow(
            """
            SELECT
                c.client_id,
                c.client_user_id,
                c.client_firstname,
                c.client_lastname,
                c.client_father_name,
                c.client_birthdate,
                c.client_gender,
                c.client_citizenship,
                c.client_address,
                c.client_telegram,
                c.client_type,
                c.client_balance,
                to_jsonb(c)->>'cashback_balance' AS cashback_balance,
                to_jsonb(c)->>'referral_code' AS referral_code,
                to_jsonb(c)->>'loyalty_tier' AS loyalty_tier,
                to_jsonb(c)->>'total_spent_amount' AS total_spent_amount,
                c.note,
                c.created_at,
                u.username,
                u.user_firstname,
                u.user_lastname
            FROM client_client_public_phone p
            JOIN client_client c ON c.client_id = p.client_id
            LEFT JOIN user_user u ON u.id = c.client_user_id
            WHERE p.public_phone = $1
              AND COALESCE(p.deleted, FALSE) = FALSE
              AND COALESCE(c.deleted, FALSE) = FALSE
            ORDER BY p.client_phone_id ASC
            LIMIT 1
            """,
            phone_number,
        )
    except (UndefinedTableError, UndefinedColumnError):
        return None
    return dict(row) if row else None


async def _get_crm_client_by_id(client_id: int | None) -> dict[str, Any] | None:
    if not client_id:
        return None
    try:
        row = await CRM_DB.fetchrow(
            """
            SELECT
                c.client_id,
                c.client_user_id,
                c.client_firstname,
                c.client_lastname,
                c.client_father_name,
                c.client_birthdate,
                c.client_gender,
                c.client_citizenship,
                c.client_address,
                c.client_telegram,
                c.client_type,
                c.client_balance,
                to_jsonb(c)->>'cashback_balance' AS cashback_balance,
                to_jsonb(c)->>'referral_code' AS referral_code,
                to_jsonb(c)->>'loyalty_tier' AS loyalty_tier,
                to_jsonb(c)->>'total_spent_amount' AS total_spent_amount,
                c.note,
                c.created_at,
                u.username,
                u.user_firstname,
                u.user_lastname
            FROM client_client c
            LEFT JOIN user_user u ON u.id = c.client_user_id
            WHERE c.client_id = $1
              AND COALESCE(c.deleted, FALSE) = FALSE
            """,
            client_id,
        )
    except (UndefinedTableError, UndefinedColumnError):
        return None
    return dict(row) if row else None


async def _get_user_by_phone(phone_number: str) -> dict[str, Any] | None:
    return await db.orm_one(select(users_t).where(users_t.c.phone_number == phone_number))


async def _remember_user_contact(
    *,
    phone_number: str,
    purpose: str,
    user: dict[str, Any] | None = None,
    crm_client_id: int | None = None,
) -> None:
    stmt = pg_insert(user_contacts_t).values(
        user_id=(user or {}).get("id"),
        phone_number=phone_number,
        crm_client_id=crm_client_id or (user or {}).get("crm_client_id"),
        source="otp",
        last_otp_purpose=purpose,
        last_seen_at=func.now(),
    )
    excluded = stmt.excluded
    await db.orm_execute(
        stmt.on_conflict_do_update(
            index_elements=[user_contacts_t.c.phone_number],
            set_={
                "user_id": func.coalesce(excluded.user_id, user_contacts_t.c.user_id),
                "crm_client_id": func.coalesce(
                    excluded.crm_client_id,
                    user_contacts_t.c.crm_client_id,
                ),
                "source": excluded.source,
                "last_otp_purpose": excluded.last_otp_purpose,
                "last_seen_at": func.now(),
                "updated_at": func.now(),
            },
        )
    )


async def _get_user_by_id(user_id: int) -> dict[str, Any]:
    row = await db.orm_one(
        select(users_t).where(users_t.c.id == user_id, users_t.c.is_active.is_(True))
    )
    if not row:
        raise HTTPException(status_code=404, detail="User was not found")
    return row


def _is_active_verified_user(user: dict[str, Any] | None) -> bool:
    return bool(user and user.get("is_active") and user.get("is_verified"))


async def _resolve_login_user(phone_number: str, user: dict[str, Any] | None) -> dict[str, Any]:
    if _is_active_verified_user(user):
        return user

    crm = await _get_crm_client_by_phone(phone_number)
    if crm:
        return await _upsert_user_from_crm(phone_number, crm)

    if user:
        return user

    raise HTTPException(
        status_code=400,
        detail={"phone_number": "Client with this phone number was not found"},
    )


async def _upsert_user_from_crm(phone_number: str, crm: dict[str, Any]) -> dict[str, Any]:
    username = crm.get("username") or phone_number
    stmt = pg_insert(users_t).values(
        username=username,
        phone_number=phone_number,
        crm_user_id=crm.get("client_user_id"),
        crm_client_id=crm.get("client_id"),
        first_name=crm.get("client_firstname") or crm.get("user_firstname"),
        last_name=crm.get("client_lastname") or crm.get("user_lastname"),
        father_name=crm.get("client_father_name"),
        birthdate=crm.get("client_birthdate"),
        gender=crm.get("client_gender"),
        citizenship=crm.get("client_citizenship"),
        address=crm.get("client_address"),
        telegram=crm.get("client_telegram"),
        is_active=True,
        is_verified=True,
    )
    excluded = stmt.excluded
    return await db.orm_one(
        stmt.on_conflict_do_update(
            index_elements=[users_t.c.phone_number],
            set_={
                "crm_user_id": func.coalesce(users_t.c.crm_user_id, excluded.crm_user_id),
                "crm_client_id": func.coalesce(users_t.c.crm_client_id, excluded.crm_client_id),
                "first_name": func.coalesce(users_t.c.first_name, excluded.first_name),
                "last_name": func.coalesce(users_t.c.last_name, excluded.last_name),
                "father_name": func.coalesce(users_t.c.father_name, excluded.father_name),
                "birthdate": func.coalesce(users_t.c.birthdate, excluded.birthdate),
                "gender": func.coalesce(users_t.c.gender, excluded.gender),
                "citizenship": func.coalesce(users_t.c.citizenship, excluded.citizenship),
                "address": func.coalesce(users_t.c.address, excluded.address),
                "telegram": func.coalesce(users_t.c.telegram, excluded.telegram),
                "is_active": True,
                "is_verified": True,
                "updated_at": func.now(),
            },
        ).returning(users_t)
    )


async def _ensure_referral_code(user_id: int) -> str:
    existing = await db.orm_scalar(
        select(referral_codes_t.c.code)
        .where(
            referral_codes_t.c.user_id == user_id,
            referral_codes_t.c.code_type == "user",
            referral_codes_t.c.is_active.is_(True),
        )
        .order_by(referral_codes_t.c.id.desc())
        .limit(1)
    )
    if existing:
        return existing

    for _ in range(10):
        code = f"SADAF-{secrets.token_hex(4).upper()}"
        inserted = await db.orm_scalar(
            pg_insert(referral_codes_t)
            .values(user_id=user_id, code=code)
            .on_conflict_do_nothing(index_elements=[referral_codes_t.c.code])
            .returning(referral_codes_t.c.code)
        )
        if inserted:
            return code
    raise HTTPException(status_code=500, detail="Referral code generation failed")


async def _cashback_balance(user_id: int) -> Decimal:
    balance = await db.orm_scalar(
        select(cashback_entries_t.c.balance_after)
        .where(cashback_entries_t.c.user_id == user_id)
        .order_by(cashback_entries_t.c.entry_id.desc())
        .limit(1)
    )
    return Decimal(str(balance or 0))


async def _referrals_count(user_id: int) -> int:
    return int(
        await db.orm_scalar(
            select(func.count())
            .select_from(referral_applications_t)
            .where(referral_applications_t.c.referrer_user_id == user_id)
        )
        or 0
    )


async def _serialize_profile(user: dict[str, Any]) -> dict[str, Any]:
    crm = await _get_crm_client_by_id(user.get("crm_client_id"))
    referral_code = await _ensure_referral_code(user["id"])
    mobile_cashback = await _cashback_balance(user["id"])

    client_balance = Decimal(str((crm or {}).get("client_balance") or 0))
    crm_cashback = Decimal(str((crm or {}).get("cashback_balance") or 0))
    total_spent = Decimal(str((crm or {}).get("total_spent_amount") or 0))
    tier = (crm or {}).get("loyalty_tier") or _tier_from_spent(total_spent)

    data = {
        "client_id": user.get("crm_client_id") or user["id"],
        "username": user.get("username"),
        "full_name": _full_name(user),
        "client_firstname": user.get("first_name") or (crm or {}).get("client_firstname"),
        "client_lastname": user.get("last_name") or (crm or {}).get("client_lastname"),
        "client_father_name": user.get("father_name") or (crm or {}).get("client_father_name"),
        "client_birthdate": user.get("birthdate") or (crm or {}).get("client_birthdate"),
        "client_gender": user.get("gender") or (crm or {}).get("client_gender"),
        "client_citizenship": user.get("citizenship") or (crm or {}).get("client_citizenship"),
        "client_address": user.get("address") or (crm or {}).get("client_address"),
        "client_telegram": user.get("telegram") or (crm or {}).get("client_telegram"),
        "client_type": (crm or {}).get("client_type") or "Basic",
        "client_balance": client_balance,
        "cashback_balance": mobile_cashback + crm_cashback,
        "referral_code": (crm or {}).get("referral_code") or referral_code,
        "loyalty_tier": tier,
        "loyalty_tier_label": TIER_LABELS.get(tier, tier),
        "total_spent_amount": total_spent,
        "note": (crm or {}).get("note"),
        "phone": user.get("phone_number"),
        "created_at": user.get("created_at"),
        "cashback_percent": _cashback_percent(tier),
    }
    return {key: _json_value(value) for key, value in data.items()}


async def me(auth_user: dict[str, Any]) -> dict[str, Any]:
    user = await _get_user_by_id(auth_user["id"])
    return await _serialize_profile(user)


async def update_me(auth_user: dict[str, Any], request: sc.MobileMeUpdateRequest) -> dict[str, Any]:
    values = request.model_dump(exclude_unset=True)
    phone = values.pop("phone", None)

    field_map = {
        "client_firstname": "first_name",
        "client_lastname": "last_name",
        "client_father_name": "father_name",
        "client_birthdate": "birthdate",
        "client_gender": "gender",
        "client_citizenship": "citizenship",
        "client_address": "address",
        "client_telegram": "telegram",
    }
    updates = {field_map[key]: value for key, value in values.items() if key in field_map}
    if phone:
        updates["phone_number"] = _normalize_phone(phone)
        updates["username"] = updates["phone_number"]

    if updates:
        await db.orm_execute(
            update(users_t)
            .where(users_t.c.id == auth_user["id"])
            .values(**updates, updated_at=func.now())
        )

    user = await _get_user_by_id(auth_user["id"])
    return await _serialize_profile(user)


async def loyalty(auth_user: dict[str, Any]) -> dict[str, Any]:
    profile = await me(auth_user)
    referrals_count = await _referrals_count(auth_user["id"])
    return {
        "client_id": profile["client_id"],
        "referral_code": profile["referral_code"],
        "referred_by": None,
        "referred_by_name": None,
        "referrals_count": referrals_count,
        "loyalty_tier": profile["loyalty_tier"],
        "loyalty_tier_label": profile["loyalty_tier_label"],
        "cashback_balance": profile["cashback_balance"],
        "total_spent_amount": profile["total_spent_amount"],
        "cashback_percent": profile["cashback_percent"],
    }


async def status(auth_user: dict[str, Any]) -> dict[str, Any]:
    profile = await me(auth_user)
    referrals_count = await _referrals_count(auth_user["id"])
    next_tier = _next_tier(profile["loyalty_tier"])
    goals = []
    if next_tier:
        goals = [
            {
                "code": "invite_friends",
                "label": "Do'stlarni taklif qilish",
                "current_value": referrals_count,
                "target_value": TIER_REFERRAL_REQUIREMENTS[next_tier],
                "unit": "ta",
                "is_done": referrals_count >= TIER_REFERRAL_REQUIREMENTS[next_tier],
            },
            {
                "code": "use_services",
                "label": "Xizmatlardan foydalanish",
                "current_value": profile["total_spent_amount"],
                "target_value": float(TIER_THRESHOLDS[next_tier]),
                "unit": "sum",
                "is_done": Decimal(str(profile["total_spent_amount"])) >= TIER_THRESHOLDS[next_tier],
            },
        ]
    return {
        "client_id": profile["client_id"],
        "full_name": profile["full_name"],
        "loyalty_tier": profile["loyalty_tier"],
        "current_tier_label": profile["loyalty_tier_label"],
        "cashback_balance": profile["cashback_balance"],
        "referral_code": profile["referral_code"],
        "progress": {
            "current_tier": profile["loyalty_tier"],
            "next_tier": next_tier,
            "next_tier_label": TIER_LABELS.get(next_tier) if next_tier else None,
            "goals": goals,
        },
        "cashback_percent": profile["cashback_percent"],
    }


async def dashboard(auth_user: dict[str, Any]) -> dict[str, Any]:
    profile = await me(auth_user)
    active_requests = await db.orm_scalar(
        select(func.count())
        .select_from(reservation_requests_t)
        .where(
            reservation_requests_t.c.user_id == auth_user["id"],
            reservation_requests_t.c.status.in_(["draft", "approved", "approved_by_patient"]),
            reservation_requests_t.c.reservation_date >= func.current_date(),
        )
    )
    unread_notifications = await db.orm_scalar(
        select(func.count())
        .select_from(notifications_t)
        .where(
            notifications_t.c.user_id == auth_user["id"],
            notifications_t.c.is_read.is_(False),
        )
    )
    referrals_count = await _referrals_count(auth_user["id"])
    next_request = await db.orm_one(
        select(
            reservation_requests_t.c.id,
            reservation_requests_t.c.crm_reservation_id,
            reservation_requests_t.c.doctor_name,
            reservation_requests_t.c.reservation_date,
            reservation_requests_t.c.reservation_time,
            reservation_requests_t.c.slot_minutes,
        )
        .where(
            reservation_requests_t.c.user_id == auth_user["id"],
            reservation_requests_t.c.status.in_(["approved", "approved_by_patient"]),
            reservation_requests_t.c.reservation_date >= func.current_date(),
        )
        .order_by(reservation_requests_t.c.reservation_date, reservation_requests_t.c.reservation_time)
        .limit(1)
    )
    return {
        "profile": profile,
        "counters": {
            "active_reservations": active_requests,
            "active_treatments": 0,
            "unread_notifications": unread_notifications,
            "referrals_count": referrals_count,
        },
        "loyalty": await loyalty(auth_user),
        "next_reservation": (
            {
                "reservation_id": next_request["crm_reservation_id"] or next_request["id"],
                "doctor_name": next_request["doctor_name"],
                "service_title": None,
                "date": next_request["reservation_date"].strftime("%d-%m-%Y"),
                "start_time": next_request["reservation_time"].strftime("%H:%M"),
                "end_time": (
                    datetime.combine(next_request["reservation_date"], next_request["reservation_time"])
                    + timedelta(minutes=next_request["slot_minutes"])
                ).strftime("%H:%M"),
            }
            if next_request
            else None
        ),
    }


async def _store_otp(
    phone_number: str,
    purpose: str,
    code: str,
    expires_at: datetime,
    language: str,
    sms_result: dict[str, Any] | None,
):
    await db.orm_execute(
        update(otp_t)
        .where(
            otp_t.c.phone_number == phone_number,
            otp_t.c.purpose == purpose,
            otp_t.c.consumed_at.is_(None),
        )
        .values(consumed_at=func.now())
    )
    await db.orm_execute(
        insert(otp_t).values(
            phone_number=phone_number,
            purpose=purpose,
            code_hash=auth_handler.get_password_hash(code),
            max_attempts=settings.MOBILE_OTP_VERIFY_MAX_ATTEMPTS,
            expires_at=expires_at,
        )
    )
    await db.orm_execute(
        insert(events_t).values(
            event_type="otp.sms.requested",
            aggregate_type="otp",
            aggregate_id=phone_number,
            payload={
                "phone_number": phone_number,
                "purpose": purpose,
                "language": language,
                "expires_at": expires_at.isoformat(),
                "sms": sms_result,
            },
        )
    )
    return expires_at


async def otp_request(request: sc.MobileOTPRequest) -> dict[str, Any]:
    phone = _normalize_phone(request.phone_number)
    user = await _get_user_by_phone(phone)
    user = await _resolve_login_user(phone, user)
    await _remember_user_contact(phone_number=phone, purpose="login", user=user)
    code, expires_at, language, sms_result = await sms.prepare_and_send_otp(phone, sms.OTP_PURPOSE_LOGIN)
    expires_at = await _store_otp(phone, "login", code, expires_at, language, sms_result)
    return {
        "message": "OTP code has been sent",
        "phone_number": phone,
        "language": language,
        "expires_at": expires_at.isoformat(),
    }


async def otp_register_request(request: sc.MobileOTPRegisterRequest) -> dict[str, Any]:
    phone = _normalize_phone(request.phone_number)
    existing_crm = await _get_crm_client_by_phone(phone)
    existing_mobile = await _get_user_by_phone(phone)
    if existing_crm or (existing_mobile and existing_mobile.get("is_verified")):
        raise HTTPException(
            status_code=400,
            detail={"phone_number": "Client with this phone number already exists. Use OTP login"},
        )

    stmt = pg_insert(users_t).values(
        username=phone,
        phone_number=phone,
        first_name=request.client_firstname,
        last_name=request.client_lastname,
        father_name=request.client_father_name,
        birthdate=request.client_birthdate,
        gender=request.client_gender,
        citizenship=request.client_citizenship,
        address=request.client_address,
        telegram=request.client_telegram,
        is_active=False,
        is_verified=False,
    )
    row = await db.orm_one(
        stmt.on_conflict_do_update(
            index_elements=[users_t.c.phone_number],
            set_={
                "first_name": stmt.excluded.first_name,
                "last_name": stmt.excluded.last_name,
                "father_name": stmt.excluded.father_name,
                "birthdate": stmt.excluded.birthdate,
                "gender": stmt.excluded.gender,
                "citizenship": stmt.excluded.citizenship,
                "address": stmt.excluded.address,
                "telegram": stmt.excluded.telegram,
                "is_active": False,
                "is_verified": False,
                "updated_at": func.now(),
            },
        ).returning(users_t)
    )
    await _remember_user_contact(phone_number=phone, purpose="register", user=row)
    code, expires_at, language, sms_result = await sms.prepare_and_send_otp(phone, sms.OTP_PURPOSE_REGISTER)
    expires_at = await _store_otp(phone, "register", code, expires_at, language, sms_result)
    return {
        "message": "OTP code has been sent",
        "phone_number": row["phone_number"],
        "language": language,
        "expires_at": expires_at.isoformat(),
    }


async def otp_verify(request: sc.MobileOTPVerify, *, purpose_hint: str | None = None):
    phone = _normalize_phone(request.phone_number)
    user = await _get_user_by_phone(phone)
    purpose = purpose_hint or "login"
    if purpose == "login":
        user = await _resolve_login_user(phone, user)
    if not user:
        raise HTTPException(status_code=400, detail={"phone_number": "OTP code was not requested"})

    code_row = await db.orm_one(
        select(otp_t)
        .where(
            otp_t.c.phone_number == phone,
            otp_t.c.purpose == purpose,
            otp_t.c.consumed_at.is_(None),
        )
        .order_by(otp_t.c.expires_at.desc())
        .limit(1)
    )
    if not code_row:
        raise HTTPException(status_code=400, detail={"otp_code": "OTP code was not requested"})
    if datetime.now(timezone.utc) > code_row["expires_at"]:
        raise HTTPException(status_code=400, detail={"otp_code": "OTP code has expired"})
    if code_row["attempts_count"] >= code_row["max_attempts"]:
        raise HTTPException(status_code=400, detail={"otp_code": "OTP attempts limit exceeded"})

    valid_test_code = settings.MOBILE_OTP_USE_TEST_CODE and request.otp_code == settings.MOBILE_OTP_TEST_CODE
    valid_hash = False if valid_test_code else auth_handler.verify_password(request.otp_code, code_row["code_hash"])
    if not (valid_test_code or valid_hash):
        await db.orm_execute(
            update(otp_t)
            .where(otp_t.c.id == code_row["id"])
            .values(attempts_count=otp_t.c.attempts_count + 1)
        )
        raise HTTPException(status_code=400, detail={"otp_code": "Invalid OTP code"})

    if purpose == "register" or not user.get("is_active") or not user.get("is_verified"):
        await db.orm_execute(
            update(users_t)
            .where(users_t.c.id == user["id"])
            .values(is_active=True, is_verified=True, updated_at=func.now())
        )

    await db.orm_execute(
        update(otp_t)
        .where(otp_t.c.id == code_row["id"])
        .values(consumed_at=func.now())
    )
    await db.orm_execute(
        update(users_t)
        .where(users_t.c.id == user["id"])
        .values(last_login_at=func.now())
    )
    user = await _get_user_by_id(user["id"])
    access = auth_handler.encode_token(user)
    refresh, _ = await auth_handler.issue_refresh_token(user["id"])
    return {
        "refresh": refresh,
        "access": access,
        "user_id": user["id"],
        "client_id": user.get("crm_client_id"),
        "username": user.get("username"),
        "user_fullname": _full_name(user),
    }


async def apply_referral_code(auth_user: dict[str, Any], request: sc.ApplyReferralCodeRequest):
    user_id = auth_user["id"]
    code = request.referral_code.strip()
    referral = await db.orm_one(
        select(referral_codes_t).where(
            func.lower(referral_codes_t.c.code) == func.lower(code),
            referral_codes_t.c.is_active.is_(True),
        )
    )
    if not referral:
        raise HTTPException(status_code=400, detail={"referral_code": "Referral code not found"})
    if referral["user_id"] == user_id:
        raise HTTPException(status_code=400, detail={"referral_code": "You cannot use your own referral code"})
    existing = await db.orm_scalar(
        select(referral_applications_t.c.id).where(referral_applications_t.c.user_id == user_id)
    )
    if existing:
        raise HTTPException(status_code=400, detail={"referral_code": "Referral code was already applied"})

    referrer_id = referral["user_id"]
    bonus = Decimal(str(referral["bonus_amount"]))
    await db.orm_execute(
        insert(referral_applications_t).values(
            user_id=user_id,
            referral_code_id=referral["id"],
            referrer_user_id=referrer_id,
        )
    )
    if referrer_id:
        balance = await _cashback_balance(referrer_id)
        await db.orm_execute(
            insert(cashback_entries_t).values(
                user_id=referrer_id,
                entry_type="referral_bonus",
                amount=bonus,
                balance_after=balance + bonus,
                related_user_id=user_id,
                note="Referral bonus",
            )
        )
    user_balance = await _cashback_balance(user_id)
    await db.orm_execute(
        insert(cashback_entries_t).values(
            user_id=user_id,
            entry_type="referral_bonus",
            amount=bonus,
            balance_after=user_balance + bonus,
            related_user_id=referrer_id,
            note="Referral bonus",
        )
    )
    return await loyalty(auth_user)
