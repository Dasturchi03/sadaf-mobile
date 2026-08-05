from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, insert, select, text, update

from app.api.mobile import schemas as sc
from app.api.auth.models.users import Users
from app.models.mobile import MobileEvent, ReservationRequest
from app.services.common import db_common as db
from app.services.mobile import notifications
from app.services.mobile.common import lang_suffix, offset_limit, paginate_rows
from app.services.mobile.reservations import doctor_detail, doctor_works
from app.utils.i18n import localized
from app.utils.di.db_ctx import CRM_DB


reservation_requests_t = ReservationRequest.__table__
events_t = MobileEvent.__table__
users_t = Users.__table__


STATUS_LABELS = {
    "draft": {"uz": "Kutilmoqda", "ru": "Ожидает", "en": "Draft"},
    "approved": {"uz": "Tasdiqlangan", "ru": "Подтверждено", "en": "Approved"},
    "approved_by_patient": {
        "uz": "Mijoz tasdiqlagan",
        "ru": "Подтверждено пациентом",
        "en": "Approved by patient",
    },
    "cancelled": {"uz": "Bekor qilingan", "ru": "Отменено", "en": "Cancelled"},
    "cancelled_by_patient": {
        "uz": "Mijoz bekor qilgan",
        "ru": "Отменено пациентом",
        "en": "Cancelled by patient",
    },
}


def _json_value(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    return value


def _status_payload(status: str, reservation_id: int | None):
    label = localized(STATUS_LABELS[status], status) if status in STATUS_LABELS else status
    return {
        "status": label,
        "status_code": status,
        "status_label": label,
        "ui_state": {
            "draft": "pending",
            "approved": "success",
            "approved_by_patient": "success",
            "cancelled": "cancelled",
            "cancelled_by_patient": "cancelled",
        }.get(status, "pending"),
        "next_action": (
            "confirm_reservation"
            if status == "approved" and reservation_id
            else "open_reservation"
            if reservation_id
            else "wait_for_clinic"
            if status == "draft"
            else "open_requests"
        ),
        "can_cancel": status in {"draft", "approved"},
        "can_confirm": status == "approved" and bool(reservation_id),
    }


async def _work(work_id: int) -> dict[str, Any]:
    lang = lang_suffix()
    row = await CRM_DB.fetchrow(
        f"""
        SELECT
            w.work_id,
            w.work_type,
            COALESCE(to_jsonb(w)->>'work_title_{lang}', w.work_title) AS work_title,
            to_jsonb(w)->>'work_title_ru' AS work_title_ru,
            to_jsonb(w)->>'work_title_en' AS work_title_en,
            to_jsonb(w)->>'work_title_uz' AS work_title_uz,
            w.work_basic_price,
            w.work_vip_price,
            w.work_discount_price,
            w.work_discount_percent
        FROM work_work w
        WHERE w.work_id = $1
          AND COALESCE(w.deleted, FALSE) = FALSE
        """,
        work_id,
    )
    if not row:
        raise HTTPException(status_code=400, detail={"reservation_work_id": "Selected service was not found"})
    return dict(row)


async def _doctor_owns_work(doctor_id: int, work_id: int) -> bool:
    return await CRM_DB.fetchval(
        """
        SELECT (
            NOT EXISTS (
                SELECT 1 FROM work_work_specialization
                WHERE work_id = $2
            )
            OR EXISTS (
                SELECT 1
                FROM work_work_specialization wws
                JOIN user_user_user_specialization uus
                  ON uus.specialization_id = wws.specialization_id
                WHERE wws.work_id = $2 AND uus.user_id = $1
            )
        )
        """,
        doctor_id,
        work_id,
    )


async def _ensure_slot_available(
    *,
    user_id: int,
    doctor_id: int,
    target_date,
    start_time,
    slot_minutes: int,
):
    end_time = (datetime.combine(target_date, start_time) + timedelta(minutes=slot_minutes)).time()
    existing_crm = await CRM_DB.fetchval(
        """
        SELECT reservation_id
        FROM reservation_reservation
        WHERE reservation_doctor_id = $1
          AND reservation_date = $2
          AND cancelled = FALSE
          AND NOT (reservation_end_time <= $3 OR reservation_start_time >= $4)
        LIMIT 1
        """,
        doctor_id,
        target_date,
        start_time,
        end_time,
    )
    if existing_crm:
        raise HTTPException(status_code=400, detail={"time": "Selected slot is already booked"})

    existing_mobile = await db.orm_scalar(
        select(reservation_requests_t.c.id)
        .where(
            reservation_requests_t.c.crm_doctor_id == doctor_id,
            reservation_requests_t.c.reservation_date == target_date,
            reservation_requests_t.c.status.in_(["draft", "approved", "approved_by_patient"]),
            text(
                "NOT ((reservation_time + (slot_minutes || ' minutes')::interval)::time <= :start_time "
                "OR reservation_time >= :end_time)"
            ),
            reservation_requests_t.c.user_id != user_id,
        )
        .params(start_time=start_time, end_time=end_time)
        .limit(1)
    )
    if existing_mobile:
        raise HTTPException(status_code=400, detail={"time": "Selected slot is already booked"})


def _serialize(row: dict[str, Any], doctor: dict[str, Any] | None, work: dict[str, Any] | None):
    status_bits = _status_payload(row["status"], row.get("crm_reservation_id"))
    return {
        "id": row["id"],
        "flutter_reservation_id": row.get("flutter_reservation_id"),
        "crm_request_id": row.get("crm_request_id"),
        "doctor": doctor,
        "reservation_work": work,
        "doctor_name": row.get("doctor_name"),
        **status_bits,
        "reservation_id": row.get("crm_reservation_id"),
        "note": row.get("note"),
        "date": row["reservation_date"].strftime("%d-%m-%Y"),
        "time": row["reservation_time"].strftime("%H:%M"),
    }


async def _mobile_user(user_id: int) -> dict[str, Any]:
    user = await db.orm_one(select(users_t).where(users_t.c.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User was not found")
    return user


async def _ensure_crm_client(auth_user: dict[str, Any]) -> int:
    if auth_user.get("crm_client_id"):
        return int(auth_user["crm_client_id"])

    user = await _mobile_user(auth_user["id"])
    phone_number = user.get("phone_number")
    if not phone_number:
        raise HTTPException(
            status_code=400,
            detail={"phone_number": "User phone number is required for CRM sync"},
        )

    existing_client_id = await CRM_DB.fetchval(
        """
        SELECT c.client_id
        FROM client_client_public_phone p
        JOIN client_client c ON c.client_id = p.client_id
        WHERE p.public_phone = $1
          AND COALESCE(p.deleted, FALSE) = FALSE
          AND COALESCE(c.deleted, FALSE) = FALSE
        ORDER BY p.client_phone_id ASC
        LIMIT 1
        """,
        phone_number,
    )
    if existing_client_id:
        await db.orm_execute(
            update(users_t)
            .where(users_t.c.id == auth_user["id"])
            .values(crm_client_id=existing_client_id, updated_at=func.now())
        )
        auth_user["crm_client_id"] = existing_client_id
        return int(existing_client_id)

    crm_client_id = await CRM_DB.fetchval(
        """
        INSERT INTO client_client(
            client_firstname, client_lastname, client_father_name, client_birthdate,
            client_gender, client_address, client_citizenship, client_telegram,
            client_type, client_balance, archive, deleted, updated_at, created_at,
            client_user_id, client_last_viewed_at, note, cashback_balance,
            loyalty_tier, referral_code, referred_by_id, total_spent_amount
        )
        VALUES (
            $1, $2, $3, COALESCE($4::date, DATE '1900-01-01'),
            COALESCE($5, 'male'), $6, COALESCE($7, 'UZ'), $8,
            'Basic', 0, FALSE, FALSE, now(), now(),
            NULL, now(), 'Created from Sadaf mobile app reservation request',
            0, 'bronze', NULL, NULL, 0
        )
        RETURNING client_id
        """,
        user.get("first_name") or "Mobile",
        user.get("last_name") or "Patient",
        user.get("father_name"),
        user.get("birthdate"),
        user.get("gender"),
        user.get("address"),
        user.get("citizenship"),
        user.get("telegram"),
    )
    await CRM_DB.execute(
        """
        INSERT INTO client_client_public_phone(
            public_phone, deleted, updated_at, created_at, client_id
        )
        VALUES ($1, FALSE, now(), now(), $2)
        """,
        phone_number,
        crm_client_id,
    )
    await db.orm_execute(
        update(users_t)
        .where(users_t.c.id == auth_user["id"])
        .values(crm_client_id=crm_client_id, updated_at=func.now())
    )
    auth_user["crm_client_id"] = crm_client_id
    return int(crm_client_id)


async def _create_crm_reservation_request(
    *,
    crm_client_id: int,
    doctor_id: int,
    work_id: int,
    flutter_reservation_id: str | None,
    doctor_name: str | None,
    note: str | None,
    target_date,
    start_time,
) -> int:
    return int(
        await CRM_DB.fetchval(
            """
            INSERT INTO reservation_reservationrequest(
                created_at, updated_at, flutter_reservation_id, status,
                doctor_name, note, date, time,
                client_id, doctor_id, reservation_id, reservation_work_id
            )
            VALUES (
                now(), now(), $1, 'draft',
                $2, $3, $4, $5,
                $6, $7, NULL, $8
            )
            RETURNING id
            """,
            flutter_reservation_id,
            doctor_name,
            note,
            target_date,
            start_time,
            crm_client_id,
            doctor_id,
            work_id,
        )
    )


async def _create_crm_doctor_notification(*, doctor_id: int, crm_request_id: int) -> None:
    await CRM_DB.execute(
        """
        INSERT INTO notifications_notification(
            notification_receiver_id, notification_reservation_id,
            notification_type, notification_message, is_read, created_at
        )
        VALUES (
            $1, NULL, 'reservation_request_created',
            'New reservation request received', FALSE, now()
        )
        """,
        doctor_id,
    )


async def _crm_request(crm_request_id: int | None) -> dict[str, Any] | None:
    if not crm_request_id:
        return None
    row = await CRM_DB.fetchrow(
        """
        SELECT id, status, reservation_id
        FROM reservation_reservationrequest
        WHERE id = $1
        """,
        crm_request_id,
    )
    return dict(row) if row else None


async def _refresh_local_from_crm(row: dict[str, Any]) -> dict[str, Any]:
    crm = await _crm_request(row.get("crm_request_id"))
    if not crm:
        return row
    if row.get("status") == crm["status"] and row.get("crm_reservation_id") == crm["reservation_id"]:
        return row
    updated = await db.orm_one(
        update(reservation_requests_t)
        .where(reservation_requests_t.c.id == row["id"])
        .values(
            status=crm["status"],
            crm_reservation_id=crm["reservation_id"],
            updated_at=func.now(),
        )
        .returning(reservation_requests_t)
    )
    return updated or row


async def _serialize_row(row: dict[str, Any]):
    row = await _refresh_local_from_crm(row)
    doctor = None
    work = None
    try:
        doctor = await doctor_detail(row["crm_doctor_id"])
    except HTTPException:
        doctor = {"id": row["crm_doctor_id"], "full_name": row.get("doctor_name")}
    try:
        work = await _work(row["crm_work_id"])
    except HTTPException:
        work = {"work_id": row["crm_work_id"]}
    return _serialize(row, doctor, {key: _json_value(value) for key, value in work.items()} if work else None)


async def list_requests(auth_user: dict[str, Any], *, page: int | None, page_size: int | None):
    offset, limit = offset_limit(page, page_size)
    count = await db.orm_scalar(
        select(func.count())
        .select_from(reservation_requests_t)
        .where(reservation_requests_t.c.user_id == auth_user["id"])
    )
    stmt = (
        select(reservation_requests_t)
        .where(reservation_requests_t.c.user_id == auth_user["id"])
        .order_by(reservation_requests_t.c.created_at.desc())
    )
    if page:
        stmt = stmt.offset(offset).limit(limit)
    rows = await db.orm_all(stmt)
    data = [await _serialize_row(row) for row in rows]
    return paginate_rows(data, count=count, page=page, page_size=page_size)


async def detail_request(auth_user: dict[str, Any], request_id: int):
    row = await db.orm_one(
        select(reservation_requests_t).where(
            reservation_requests_t.c.id == request_id,
            reservation_requests_t.c.user_id == auth_user["id"],
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Reservation request was not found")
    return await _serialize_row(row)


async def create_request(auth_user: dict[str, Any], request: sc.MobileReservationRequestCreate):
    slot_minutes = max(request.slot_minutes or 60, 15)
    doctor = await doctor_detail(request.doctor_id)
    work = await _work(request.reservation_work_id)
    if not await _doctor_owns_work(request.doctor_id, request.reservation_work_id):
        raise HTTPException(
            status_code=400,
            detail={"reservation_work_id": "Selected service does not belong to this doctor"},
        )
    await _ensure_slot_available(
        user_id=auth_user["id"],
        doctor_id=request.doctor_id,
        target_date=request.date,
        start_time=request.time,
        slot_minutes=slot_minutes,
    )
    async with CRM_DB.transaction():
        crm_client_id = await _ensure_crm_client(auth_user)
        crm_request_id = await _create_crm_reservation_request(
            crm_client_id=crm_client_id,
            doctor_id=request.doctor_id,
            work_id=request.reservation_work_id,
            flutter_reservation_id=request.flutter_reservation_id,
            doctor_name=doctor.get("full_name"),
            note=request.note,
            target_date=request.date,
            start_time=request.time,
        )
        await _create_crm_doctor_notification(
            doctor_id=request.doctor_id,
            crm_request_id=crm_request_id,
        )
        row = await db.orm_one(
            insert(reservation_requests_t)
            .values(
                user_id=auth_user["id"],
                crm_client_id=crm_client_id,
                crm_doctor_id=request.doctor_id,
                crm_work_id=request.reservation_work_id,
                crm_request_id=crm_request_id,
                flutter_reservation_id=request.flutter_reservation_id,
                doctor_name=doctor.get("full_name"),
                status="draft",
                note=request.note,
                reservation_date=request.date,
                reservation_time=request.time,
                slot_minutes=slot_minutes,
            )
            .returning(reservation_requests_t)
        )
    await db.orm_execute(
        insert(events_t).values(
            event_type="reservation_request.created",
            aggregate_type="reservation_request",
            aggregate_id=str(row["id"]),
            payload={
                "request_id": row["id"],
                "user_id": auth_user["id"],
                "crm_client_id": row.get("crm_client_id"),
                "crm_request_id": row.get("crm_request_id"),
                "crm_doctor_id": request.doctor_id,
                "crm_work_id": request.reservation_work_id,
                "date": request.date.isoformat(),
                "time": request.time.strftime("%H:%M"),
            },
        )
    )
    await notifications.create_notification(
        user_id=auth_user["id"],
        notification_type="reservation_request",
        message=localized(
            {
                "uz": "Qabul so'rovingiz qabul qilindi",
                "ru": "Ваша заявка на запись принята",
                "en": "Your reservation request was received",
            },
            "Your reservation request was received",
        ),
        crm_reservation_id=row.get("crm_reservation_id"),
        payload={
            "reservation_request_id": row["id"],
            "doctor_name": doctor.get("full_name"),
            "service_title": work.get("work_title"),
            "date": request.date.isoformat(),
            "time": request.time.strftime("%H:%M"),
        },
    )
    return _serialize(
        dict(row),
        doctor,
        {key: _json_value(value) for key, value in work.items()},
    )


async def cancel_request(auth_user: dict[str, Any], request_id: int):
    existing = await db.orm_one(
        select(reservation_requests_t).where(
            reservation_requests_t.c.id == request_id,
            reservation_requests_t.c.user_id == auth_user["id"],
        )
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Reservation request was not found")
    existing = await _refresh_local_from_crm(existing)
    if existing["status"] in {"cancelled", "cancelled_by_patient"}:
        raise HTTPException(status_code=400, detail="Reservation request is already cancelled")

    async with CRM_DB.transaction():
        if existing.get("crm_request_id"):
            await CRM_DB.execute(
                """
                UPDATE reservation_reservationrequest
                SET status = 'cancelled_by_patient', updated_at = now()
                WHERE id = $1
                """,
                existing["crm_request_id"],
            )
        if existing.get("crm_reservation_id"):
            await CRM_DB.execute(
                """
                UPDATE reservation_reservation
                SET cancelled = TRUE, cancelled_by_patient = TRUE
                WHERE reservation_id = $1
                """,
                existing["crm_reservation_id"],
            )
        row = await db.orm_one(
            update(reservation_requests_t)
            .where(
                reservation_requests_t.c.id == request_id,
                reservation_requests_t.c.user_id == auth_user["id"],
            )
            .values(status="cancelled_by_patient", updated_at=func.now())
            .returning(reservation_requests_t)
        )
    await db.orm_execute(
        insert(events_t).values(
            event_type="reservation_request.cancelled_by_patient",
            aggregate_type="reservation_request",
            aggregate_id=str(row["id"]),
            payload={
                "request_id": row["id"],
                "user_id": auth_user["id"],
                "crm_request_id": row.get("crm_request_id"),
                "crm_reservation_id": row.get("crm_reservation_id"),
            },
        )
    )
    return await _serialize_row(row)


async def confirm_request(auth_user: dict[str, Any], request_id: int):
    existing = await db.orm_one(
        select(reservation_requests_t).where(
            reservation_requests_t.c.id == request_id,
            reservation_requests_t.c.user_id == auth_user["id"],
        )
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Reservation request was not found")
    existing = await _refresh_local_from_crm(existing)
    if existing["status"] != "approved" or not existing.get("crm_reservation_id"):
        raise HTTPException(
            status_code=400,
            detail="Only clinic-approved requests with reservation can be confirmed",
        )

    async with CRM_DB.transaction():
        await CRM_DB.execute(
            """
            UPDATE reservation_reservationrequest
            SET status = 'approved_by_patient', updated_at = now()
            WHERE id = $1
            """,
            existing["crm_request_id"],
        )
        row = await db.orm_one(
            update(reservation_requests_t)
            .where(
                reservation_requests_t.c.id == request_id,
                reservation_requests_t.c.user_id == auth_user["id"],
                reservation_requests_t.c.status == "approved",
            )
            .values(status="approved_by_patient", updated_at=func.now())
            .returning(reservation_requests_t)
        )
    if not row:
        raise HTTPException(status_code=404, detail="Reservation request was not found")
    await db.orm_execute(
        insert(events_t).values(
            event_type="reservation_request.confirmed",
            aggregate_type="reservation_request",
            aggregate_id=str(row["id"]),
            payload={"request_id": row["id"], "user_id": auth_user["id"]},
        )
    )
    return await _serialize_row(row)
