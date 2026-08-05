from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.mobile import ReservationRequest
from app.services.common import db_common as db
from app.services.mobile.common import as_dict, as_list, lang_suffix, offset_limit, paginate_rows
from app.utils.di.db_ctx import CRM_DB
from app.utils.i18n import localized


reservation_requests_t = ReservationRequest.__table__


DOCTOR_TYPE_NAMES = ("Doctor", "Доктор")
WEEKDAY_NAMES = {
    0: ("0", "monday", "mon"),
    1: ("1", "tuesday", "tue"),
    2: ("2", "wednesday", "wed"),
    3: ("3", "thursday", "thu"),
    4: ("4", "friday", "fri"),
    5: ("5", "saturday", "sat"),
    6: ("6", "sunday", "sun"),
}

REQUEST_STATUS_LABELS = {
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
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    return value


def _time_value(value: Any) -> str | None:
    return value.strftime("%H:%M") if value else None


def _request_status_label(status: str | None) -> str | None:
    if not status:
        return None
    return localized(REQUEST_STATUS_LABELS.get(status, {}), status)


def _serialize_doctor(row: dict[str, Any]) -> dict[str, Any] | None:
    doctor_id = row.get("doctor_id")
    if not doctor_id:
        return None
    full_name = " ".join(
        part for part in [row.get("user_firstname"), row.get("user_lastname")] if part
    )
    return {
        "id": doctor_id,
        "user_firstname": row.get("user_firstname"),
        "user_lastname": row.get("user_lastname"),
        "user_image": row.get("user_image"),
        "full_name": full_name or None,
    }


def _serialize_work(row: dict[str, Any]) -> dict[str, Any] | None:
    work_id = row.get("work_id")
    if not work_id:
        return None
    return {
        "work_id": work_id,
        "work_type": row.get("work_type"),
        "work_title": row.get("work_title"),
        "work_title_ru": row.get("work_title_ru"),
        "work_title_en": row.get("work_title_en"),
        "work_title_uz": row.get("work_title_uz"),
        "work_basic_price": _json_value(row.get("work_basic_price")),
        "work_vip_price": _json_value(row.get("work_vip_price")),
        "work_discount_price": _json_value(row.get("work_discount_price")),
        "work_discount_percent": _json_value(row.get("work_discount_percent")),
    }


def _serialize_client(row: dict[str, Any]) -> dict[str, Any] | None:
    client_id = row.get("client_id")
    if not client_id:
        return None
    return {
        "client_id": client_id,
        "client_firstname": row.get("client_firstname"),
        "client_lastname": row.get("client_lastname"),
        "client_birthdate": _json_value(row.get("client_birthdate")),
        "public_phone": row.get("public_phone"),
    }


def _serialize_reservation(row: dict[str, Any], *, include_client: bool = False) -> dict[str, Any]:
    data = {
        "reservation_id": row["reservation_id"],
        "reservation_doctor": _serialize_doctor(row),
        "reservation_work": _serialize_work(row),
        "reservation_notes": row.get("reservation_notes"),
        "reservation_date": _json_value(row.get("reservation_date")),
        "reservation_start_time": _time_value(row.get("reservation_start_time")),
        "reservation_end_time": _time_value(row.get("reservation_end_time")),
        "is_initial": row.get("is_initial"),
        "cancelled": row.get("cancelled"),
        "cancelled_by_patient": row.get("cancelled_by_patient"),
        "request_status": _request_status_label(row.get("request_status_code")),
        "request_status_code": row.get("request_status_code"),
        "reservation_request_id": row.get("reservation_request_id"),
        "created_at": _json_value(row.get("created_at")),
    }
    if include_client:
        data["reservation_client"] = _serialize_client(row)
    return data


async def _reservation_rows_query(where_sql: str, *, order_sql: str = "ORDER BY r.reservation_date, r.reservation_start_time"):
    lang = lang_suffix()
    return f"""
        SELECT
            r.reservation_id,
            r.reservation_notes,
            r.reservation_date,
            r.reservation_start_time,
            r.reservation_end_time,
            r.is_initial,
            r.cancelled,
            r.cancelled_by_patient,
            r.created_at,
            u.id AS doctor_id,
            u.user_firstname,
            u.user_lastname,
            to_jsonb(u)->>'user_image' AS user_image,
            w.work_id,
            w.work_type,
            COALESCE(to_jsonb(w)->>'work_title_{lang}', w.work_title) AS work_title,
            to_jsonb(w)->>'work_title_ru' AS work_title_ru,
            to_jsonb(w)->>'work_title_en' AS work_title_en,
            to_jsonb(w)->>'work_title_uz' AS work_title_uz,
            w.work_basic_price,
            w.work_vip_price,
            w.work_discount_price,
            w.work_discount_percent,
            c.client_id,
            c.client_firstname,
            c.client_lastname,
            c.client_birthdate,
            (
                SELECT p.public_phone
                FROM client_client_public_phone p
                WHERE p.client_id = c.client_id
                  AND COALESCE(p.deleted, FALSE) = FALSE
                ORDER BY p.client_phone_id ASC
                LIMIT 1
            ) AS public_phone,
            rr.id AS reservation_request_id,
            rr.status AS request_status_code
        FROM reservation_reservation r
        LEFT JOIN user_user u ON u.id = r.reservation_doctor_id
        LEFT JOIN work_work w ON w.work_id = r.reservation_work_id
        LEFT JOIN client_client c ON c.client_id = r.reservation_client_id
        LEFT JOIN reservation_reservationrequest rr ON rr.reservation_id = r.reservation_id
        WHERE {where_sql}
        {order_sql}
    """


async def _work_detail(work_id: int | None) -> dict[str, Any] | None:
    if not work_id:
        return None
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
        """,
        work_id,
    )
    return _serialize_work(dict(row)) if row else None


async def _serialize_pending_request(row: dict[str, Any]) -> dict[str, Any]:
    doctor = None
    try:
        doctor = await doctor_detail(row["crm_doctor_id"])
    except HTTPException:
        doctor = {
            "id": row["crm_doctor_id"],
            "user_firstname": None,
            "user_lastname": None,
            "user_image": None,
            "full_name": row.get("doctor_name"),
        }
    work = await _work_detail(row.get("crm_work_id"))
    return {
        "reservation_id": row.get("crm_reservation_id"),
        "reservation_doctor": doctor,
        "reservation_work": work,
        "reservation_notes": row.get("note"),
        "reservation_date": _json_value(row.get("reservation_date")),
        "reservation_start_time": _time_value(row.get("reservation_time")),
        "reservation_end_time": _time_value(
            (
                datetime.combine(row["reservation_date"], row["reservation_time"])
                + timedelta(minutes=row["slot_minutes"])
            ).time()
        ),
        "is_initial": False,
        "cancelled": False,
        "cancelled_by_patient": False,
        "request_status": _request_status_label(row.get("status")),
        "request_status_code": row.get("status"),
        "reservation_request_id": row["id"],
        "crm_request_id": row.get("crm_request_id"),
        "created_at": _json_value(row.get("created_at")),
        "source": "reservation_request",
        "is_pending": row.get("status") == "draft",
    }


async def _pending_request_rows(user_id: int) -> list[dict[str, Any]]:
    rows = await db.orm_all(
        select(reservation_requests_t)
        .where(
            reservation_requests_t.c.user_id == user_id,
            reservation_requests_t.c.status == "draft",
            reservation_requests_t.c.reservation_date >= func.current_date(),
        )
        .order_by(reservation_requests_t.c.reservation_date, reservation_requests_t.c.reservation_time)
    )
    return [await _serialize_pending_request(row) for row in rows]


async def user_reservation_count(client_id: int | None, *, status: str | None = "active") -> int:
    if not client_id:
        return 0
    where = ["r.reservation_client_id = $1"]
    args = [client_id]
    if status == "active":
        where.extend(["r.cancelled = FALSE", "r.reservation_date >= CURRENT_DATE"])
    elif status == "history":
        where.extend(["r.cancelled = FALSE", "r.reservation_date < CURRENT_DATE"])
    elif status == "cancelled":
        where.append("r.cancelled = TRUE")
    return int(
        await CRM_DB.fetchval(
            f"""
            SELECT COUNT(*)
            FROM reservation_reservation r
            WHERE {' AND '.join(where)}
            """,
            *args,
        )
        or 0
    )


async def next_user_reservation(client_id: int | None) -> dict[str, Any] | None:
    if not client_id:
        return None
    query = await _reservation_rows_query(
        """
        r.reservation_client_id = $1
        AND r.cancelled = FALSE
        AND r.reservation_date >= CURRENT_DATE
        """,
        order_sql="ORDER BY r.reservation_date, r.reservation_start_time LIMIT 1",
    )
    row = await CRM_DB.fetchrow(query, client_id)
    return _serialize_reservation(dict(row)) if row else None


async def list_user_reservations(
    auth_user: dict[str, Any],
    *,
    status: str | None,
    page: int | None,
    page_size: int | None,
):
    client_id = auth_user.get("crm_client_id")
    if not client_id:
        return paginate_rows([], count=0, page=page, page_size=page_size)

    where = ["r.reservation_client_id = $1"]
    args: list[Any] = [client_id]
    if status == "active":
        where.extend(["r.cancelled = FALSE", "r.reservation_date >= CURRENT_DATE"])
    elif status == "history":
        where.extend(["r.cancelled = FALSE", "r.reservation_date < CURRENT_DATE"])
    elif status == "cancelled":
        where.append("r.cancelled = TRUE")

    query = await _reservation_rows_query(
        " AND ".join(where),
        order_sql="ORDER BY r.reservation_date DESC, r.reservation_start_time DESC",
    )
    rows = [_serialize_reservation(dict(row)) for row in await CRM_DB.fetch(query, *args)]
    if status in {None, "active"}:
        rows.extend(await _pending_request_rows(auth_user["id"]))
    rows.sort(
        key=lambda row: (
            row.get("reservation_date") or "",
            row.get("reservation_start_time") or "",
            row.get("reservation_request_id") or row.get("reservation_id") or 0,
        ),
        reverse=True,
    )
    count = len(rows)
    offset, limit = offset_limit(page, page_size)
    if limit is not None:
        rows = rows[offset : offset + limit]
    return paginate_rows(rows, count=count, page=page, page_size=page_size)


async def user_reservation_detail(auth_user: dict[str, Any], reservation_id: int):
    client_id = auth_user.get("crm_client_id")
    if not client_id:
        raise HTTPException(status_code=404, detail="Reservation was not found")
    query = await _reservation_rows_query(
        "r.reservation_id = $1 AND r.reservation_client_id = $2",
        order_sql="",
    )
    row = await CRM_DB.fetchrow(query, reservation_id, client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Reservation was not found")
    return _serialize_reservation(dict(row), include_client=True)


async def pending_request_count(user_id: int) -> int:
    return int(
        await db.orm_scalar(
            select(func.count())
            .select_from(reservation_requests_t)
            .where(
                reservation_requests_t.c.user_id == user_id,
                reservation_requests_t.c.status == "draft",
                reservation_requests_t.c.reservation_date >= func.current_date(),
            )
        )
        or 0
    )


async def doctors(specialization: str | None = None, category_id: int | None = None):
    args = [list(DOCTOR_TYPE_NAMES)]
    where = ["ut.type_text = ANY($1::text[])"]
    if specialization:
        args.append(specialization)
        where.append(
            f"""
            EXISTS (
                SELECT 1
                FROM user_user_user_specialization uus
                JOIN specialization_specialization s
                  ON s.specialization_id = uus.specialization_id
                WHERE uus.user_id = u.id
                  AND (s.specialization_text ILIKE ${len(args)}
                       OR s.specialization_id::text = ${len(args)})
            )
            """
        )
    if category_id:
        args.append(category_id)
        where.append(
            f"""
            EXISTS (
                SELECT 1
                FROM user_user_user_specialization uus
                JOIN work_work_specialization wws
                  ON wws.specialization_id = uus.specialization_id
                JOIN work_work_category wwc
                  ON wwc.work_id = wws.work_id
                WHERE uus.user_id = u.id
                  AND wwc.category_id = ${len(args)}
            )
            """
        )

    rows = await CRM_DB.fetch(
        f"""
        SELECT
            u.id,
            u.user_firstname,
            u.user_lastname,
            to_jsonb(u)->>'user_image' AS user_image,
            concat_ws(' ', u.user_firstname, u.user_lastname) AS full_name,
            'available' AS status,
            0 AS available_slots_count,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'specialization_id', s.specialization_id,
                            'specialization_text', s.specialization_text
                        )
                    )
                    FROM user_user_user_specialization uus
                    JOIN specialization_specialization s
                      ON s.specialization_id = uus.specialization_id
                    WHERE uus.user_id = u.id
                ),
                '[]'::jsonb
            ) AS user_specialization
        FROM user_user u
        JOIN user_user_type ut ON ut.user_type_id = u.user_type_id
        WHERE {' AND '.join(where)}
        ORDER BY u.user_firstname, u.user_lastname
        """,
        *args,
    )
    return as_list(rows)


async def doctor_detail(doctor_id: int):
    row = await CRM_DB.fetchrow(
        """
        SELECT
            u.id,
            u.user_firstname,
            u.user_lastname,
            to_jsonb(u)->>'user_image' AS user_image,
            concat_ws(' ', u.user_firstname, u.user_lastname) AS full_name,
            'available' AS status,
            '[]'::jsonb AS available_slots,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'specialization_id', s.specialization_id,
                            'specialization_text', s.specialization_text
                        )
                    )
                    FROM user_user_user_specialization uus
                    JOIN specialization_specialization s
                      ON s.specialization_id = uus.specialization_id
                    WHERE uus.user_id = u.id
                ),
                '[]'::jsonb
            ) AS user_specialization
        FROM user_user u
        JOIN user_user_type ut ON ut.user_type_id = u.user_type_id
        WHERE u.id = $1 AND ut.type_text = ANY($2::text[])
        """,
        doctor_id,
        list(DOCTOR_TYPE_NAMES),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return as_dict(row)


async def doctor_works(doctor_id: int):
    lang = lang_suffix()
    rows = await CRM_DB.fetch(
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
            w.work_discount_percent,
            COALESCE((to_jsonb(w)->>'estimated_duration_days')::int, 7)
                AS estimated_duration_days,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'category_id', c.category_id,
                            'category_title', COALESCE(to_jsonb(c)->>'category_title_{lang}', c.category_title)
                        )
                    )
                    FROM work_work_category wwc
                    JOIN category_category c ON c.category_id = wwc.category_id
                    WHERE wwc.work_id = w.work_id
                ),
                '[]'::jsonb
            ) AS category,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'specialization_id', s.specialization_id,
                            'specialization_text', s.specialization_text
                        )
                    )
                    FROM work_work_specialization wws
                    JOIN specialization_specialization s
                      ON s.specialization_id = wws.specialization_id
                    WHERE wws.work_id = w.work_id
                ),
                '[]'::jsonb
            ) AS specialization
        FROM work_work w
        WHERE COALESCE(w.deleted, FALSE) = FALSE
          AND (
            NOT EXISTS (
                SELECT 1 FROM work_work_specialization wws
                WHERE wws.work_id = w.work_id
            )
            OR EXISTS (
                SELECT 1
                FROM work_work_specialization wws
                JOIN user_user_user_specialization uus
                  ON uus.specialization_id = wws.specialization_id
                WHERE wws.work_id = w.work_id AND uus.user_id = $1
            )
          )
        ORDER BY w.work_title
        """,
        doctor_id,
    )
    return as_list(rows)


async def doctor_slots(doctor_id: int, date_value: str, slot_minutes: int = 60):
    try:
        target_date = datetime.strptime(date_value, "%d-%m-%Y").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Неверный формат даты")

    slot_minutes = max(slot_minutes or 60, 15)
    doctor = await doctor_detail(doctor_id)
    aliases = WEEKDAY_NAMES[target_date.weekday()]
    schedule = await CRM_DB.fetchrow(
        """
        SELECT work_start_time, work_end_time, lunch_start_time, lunch_end_time
        FROM user_userschedule
        WHERE user_id = $1
          AND is_working = TRUE
          AND lower(day) = ANY($2::text[])
        LIMIT 1
        """,
        doctor_id,
        list(aliases),
    )
    if not schedule:
        return {
            "doctor_id": doctor_id,
            "doctor_name": doctor["full_name"],
            "date": date_value,
            "slot_minutes": slot_minutes,
            "slots": [],
        }

    crm_reservations = await CRM_DB.fetch(
        """
        SELECT reservation_start_time, reservation_end_time
        FROM reservation_reservation
        WHERE reservation_doctor_id = $1
          AND reservation_date = $2
          AND cancelled = FALSE
        """,
        doctor_id,
        target_date,
    )
    mobile_requests = await db.orm_all(
        select(reservation_requests_t.c.reservation_time, reservation_requests_t.c.slot_minutes).where(
            reservation_requests_t.c.crm_doctor_id == doctor_id,
            reservation_requests_t.c.reservation_date == target_date,
            reservation_requests_t.c.status.in_(["draft", "approved", "approved_by_patient"]),
        )
    )

    busy = [
        (row["reservation_start_time"], row["reservation_end_time"])
        for row in crm_reservations
    ]
    for row in mobile_requests:
        start = row["reservation_time"]
        end = (datetime.combine(target_date, start) + timedelta(minutes=row["slot_minutes"])).time()
        busy.append((start, end))

    current_dt = datetime.combine(target_date, schedule["work_start_time"])
    end_dt = datetime.combine(target_date, schedule["work_end_time"])
    delta = timedelta(minutes=slot_minutes)
    slots = []
    while current_dt + delta <= end_dt:
        slot_start = current_dt.time()
        slot_end = (current_dt + delta).time()
        overlaps_lunch = False
        if schedule["lunch_start_time"] and schedule["lunch_end_time"]:
            overlaps_lunch = not (
                slot_end <= schedule["lunch_start_time"]
                or slot_start >= schedule["lunch_end_time"]
            )
        is_booked = any(not (slot_end <= start or slot_start >= end) for start, end in busy)
        slots.append(
            {
                "start": slot_start.strftime("%H:%M"),
                "end": slot_end.strftime("%H:%M"),
                "is_booked": is_booked,
                "is_available": not overlaps_lunch and not is_booked,
            }
        )
        current_dt += delta

    return {
        "doctor_id": doctor_id,
        "doctor_name": doctor["full_name"],
        "date": date_value,
        "slot_minutes": slot_minutes,
        "slots": slots,
    }
