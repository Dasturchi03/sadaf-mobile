from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select

from app.models.mobile import ReservationRequest
from app.services.common import db_common as db
from app.services.mobile.common import as_dict, as_list, lang_suffix
from app.utils.di.db_ctx import CRM_DB


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
