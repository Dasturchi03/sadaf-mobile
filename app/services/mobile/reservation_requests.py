from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, insert, select, text, update

from app.api.mobile import schemas as sc
from app.models.mobile import MobileEvent, ReservationRequest
from app.services.common import db_common as db
from app.services.mobile import notifications
from app.services.mobile.common import lang_suffix, offset_limit, paginate_rows
from app.services.mobile.reservations import doctor_detail, doctor_works
from app.utils.i18n import localized
from app.utils.di.db_ctx import CRM_DB


reservation_requests_t = ReservationRequest.__table__
events_t = MobileEvent.__table__


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
        "doctor": doctor,
        "reservation_work": work,
        "doctor_name": row.get("doctor_name"),
        **status_bits,
        "reservation_id": row.get("crm_reservation_id"),
        "note": row.get("note"),
        "date": row["reservation_date"].strftime("%d-%m-%Y"),
        "time": row["reservation_time"].strftime("%H:%M"),
    }


async def _serialize_row(row: dict[str, Any]):
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
    row = await db.orm_one(
        insert(reservation_requests_t)
        .values(
            user_id=auth_user["id"],
            crm_client_id=auth_user.get("crm_client_id"),
            crm_doctor_id=request.doctor_id,
            crm_work_id=request.reservation_work_id,
            flutter_reservation_id=request.flutter_reservation_id,
            doctor_name=doctor.get("full_name"),
            status="approved_by_patient",
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
                "crm_client_id": auth_user.get("crm_client_id"),
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


async def confirm_request(auth_user: dict[str, Any], request_id: int):
    row = await db.orm_one(
        update(reservation_requests_t)
        .where(
            reservation_requests_t.c.id == request_id,
            reservation_requests_t.c.user_id == auth_user["id"],
            reservation_requests_t.c.status.in_(["draft", "approved", "approved_by_patient"]),
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
