from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from asyncpg.exceptions import UndefinedColumnError, UndefinedTableError
from fastapi import HTTPException

from app.services.mobile import demo_account
from app.services.mobile.common import lang_suffix, offset_limit, paginate_rows
from app.utils.di.db_ctx import CRM_DB
from app.utils.i18n import localized


STATUS_LABELS = {
    "accepted": {"uz": "Qabul", "ru": "Прием", "en": "Accepted"},
    "in_progress": {"uz": "Jarayonda", "ru": "В процессе", "en": "In progress"},
    "completed": {"uz": "O'tilgan", "ru": "Завершено", "en": "Completed"},
}
PAYMENT_LABELS = {
    "paid": {"uz": "To'langan", "ru": "Оплачено", "en": "Paid"},
    "partial": {"uz": "Qisman to'langan", "ru": "Частично оплачено", "en": "Partially paid"},
    "unpaid": {"uz": "To'lanmagan", "ru": "Не оплачено", "en": "Unpaid"},
}


def _json_value(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return value


def _doctor_name(row: dict[str, Any]) -> str | None:
    return " ".join(
        part for part in [row.get("user_firstname"), row.get("user_lastname")] if part
    ) or None


def _duration_label(days: int | None) -> str | None:
    if not days:
        return None
    if days % 7 == 0:
        return localized({"uz": f"{days // 7} hafta", "ru": f"{days // 7} нед.", "en": f"{days // 7} weeks"})
    return localized({"uz": f"{days} kun", "ru": f"{days} дн.", "en": f"{days} days"})


async def _actions(card_id: int) -> list[dict[str, Any]]:
    lang = lang_suffix()
    rows = await CRM_DB.fetch(
        f"""
        SELECT
            a.action_id,
            a.action_stage_id,
            a.action_note,
            a.action_price,
            a.action_is_done,
            a.action_is_paid,
            a.action_finished_at,
            s.stage_id,
            s.stage_index,
            s.stage_is_done,
            s.stage_is_paid,
            t.tooth_id,
            t.tooth_number,
            w.work_id,
            COALESCE(to_jsonb(w)->>'work_title_{lang}', w.work_title) AS work_title,
            COALESCE((to_jsonb(w)->>'estimated_duration_days')::int, 7)
                AS estimated_duration_days,
            u.id AS doctor_id,
            u.user_firstname,
            u.user_lastname,
            r.reservation_id,
            r.reservation_date,
            r.reservation_start_time,
            r.reservation_end_time
        FROM medcard_action a
        JOIN medcard_stage s ON s.stage_id = a.action_stage_id
        LEFT JOIN medcard_tooth t ON t.tooth_id = s.tooth_id
        LEFT JOIN work_work w ON w.work_id = a.action_work_id
        LEFT JOIN user_user u ON u.id = a.action_doctor_id
        LEFT JOIN reservation_reservation r ON r.reservation_id = a.action_date_id
        WHERE s.card_id = $1
          AND COALESCE(a.deleted, FALSE) = FALSE
          AND COALESCE(s.deleted, FALSE) = FALSE
        ORDER BY s.stage_index, a.action_id
        """,
        card_id,
    )
    return [dict(row) for row in rows]


async def _paid_amount(card_id: int) -> Decimal:
    try:
        value = await CRM_DB.fetchval(
            """
            SELECT COALESCE(SUM(transaction_sum), 0)
            FROM transaction_transaction
            WHERE transaction_card_id = $1
            """,
            card_id,
        )
    except UndefinedTableError:
        value = 0
    return Decimal(str(value or 0))


def _latest_reservation(actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    reservations = [row for row in actions if row.get("reservation_id")]
    if not reservations:
        return None
    return sorted(
        reservations,
        key=lambda row: (
            row["reservation_date"],
            row["reservation_start_time"],
            row["reservation_id"],
        ),
        reverse=True,
    )[0]


def _plan_titles(actions: list[dict[str, Any]]) -> list[str]:
    titles = []
    seen = set()
    for row in actions:
        title = row.get("work_title")
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def _status(card: dict[str, Any], actions: list[dict[str, Any]]) -> str:
    if card["card_is_done"]:
        return "completed"
    if any(row["action_is_done"] for row in actions):
        return "in_progress"
    if _latest_reservation(actions):
        return "accepted"
    return "in_progress"


def _payment_status(card: dict[str, Any], paid_amount: Decimal) -> str:
    if card["card_is_paid"]:
        return "paid"
    if paid_amount > 0:
        return "partial"
    return "unpaid"


def _doctors(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    doctors = []
    for row in actions:
        doctor_id = row.get("doctor_id")
        if not doctor_id or doctor_id in seen:
            continue
        seen.add(doctor_id)
        doctors.append(
            {
                "id": doctor_id,
                "user_firstname": row.get("user_firstname"),
                "user_lastname": row.get("user_lastname"),
                "full_name": _doctor_name(row),
            }
        )
    return doctors


def _reservation_summary(actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    row = _latest_reservation(actions)
    if not row:
        return None
    return {
        "reservation_id": row["reservation_id"],
        "reservation_request_id": None,
        "date": row["reservation_date"].strftime("%d-%m-%Y"),
        "start_time": row["reservation_start_time"].strftime("%H:%M"),
        "end_time": row["reservation_end_time"].strftime("%H:%M"),
        "doctor_name": _doctor_name(row),
        "service_title": row.get("work_title"),
        "is_initial": False,
    }


async def _serialize_card(card: dict[str, Any], *, detail: bool = False):
    actions = await _actions(card["card_id"])
    paid = await _paid_amount(card["card_id"])
    total_price = Decimal(str(card.get("card_discount_price") or card.get("card_price") or 0))
    remaining = max(total_price - paid, Decimal("0"))
    status = _status(card, actions)
    payment_status = _payment_status(card, paid)
    doctors = _doctors(actions)
    plan_titles = _plan_titles(actions)
    reservation_summary = _reservation_summary(actions)

    data = {
        "card_id": card["card_id"],
        "card_number": f"N {card['card_id']}",
        "card_price": _json_value(card.get("card_price")),
        "card_discount_price": _json_value(card.get("card_discount_price")),
        "card_discount_percent": card.get("card_discount_percent"),
        "card_is_done": card.get("card_is_done"),
        "card_is_paid": card.get("card_is_paid"),
        "card_finished_at": _json_value(card.get("card_finished_at")),
        "doctors": doctors,
        "doctor_name": doctors[0]["full_name"] if doctors else None,
        "paid_amount": _json_value(paid),
        "remaining_amount": _json_value(remaining),
        "total_price": _json_value(total_price),
        "reservation_request_id": None,
        "status": status,
        "status_label": localized(STATUS_LABELS[status], status) if status in STATUS_LABELS else status,
        "payment_status": payment_status,
        "payment_status_label": (
            localized(PAYMENT_LABELS[payment_status], payment_status)
            if payment_status in PAYMENT_LABELS
            else payment_status
        ),
        "reservation_summary": reservation_summary,
        "reservation_datetime": (
            f"{reservation_summary['date']}, {reservation_summary['start_time']} - {reservation_summary['end_time']}"
            if reservation_summary
            else None
        ),
        "treatment_plan_summary": (
            ", ".join(plan_titles)
            if len(plan_titles) <= 3
            else ", ".join(plan_titles[:3]) + f" +{len(plan_titles) - 3}"
            if plan_titles
            else None
        ),
        "treatment_plan_count": len(plan_titles),
        "card_created_at": _json_value(card.get("card_created_at")),
    }

    if not detail:
        return data

    stages = {}
    treatment_plan = []
    for row in actions:
        stage = stages.setdefault(
            row["stage_id"],
            {
                "stage_id": row["stage_id"],
                "stage_index": row["stage_index"],
                "stage_is_done": row["stage_is_done"],
                "stage_is_paid": row["stage_is_paid"],
                "tooth": {
                    "tooth_id": row["tooth_id"],
                    "tooth_number": row["tooth_number"],
                }
                if row["tooth_id"]
                else None,
                "action_stage": [],
            },
        )
        action_item = {
            "action_id": row["action_id"],
            "action_work_title": row.get("work_title"),
            "doctor": {
                "id": row["doctor_id"],
                "user_firstname": row.get("user_firstname"),
                "user_lastname": row.get("user_lastname"),
                "full_name": _doctor_name(row),
            }
            if row["doctor_id"]
            else None,
            "action_note": row.get("action_note"),
            "action_price": _json_value(row.get("action_price")),
            "action_is_done": row.get("action_is_done"),
            "action_is_paid": row.get("action_is_paid"),
            "action_finished_at": _json_value(row.get("action_finished_at")),
        }
        stage["action_stage"].append(action_item)
        treatment_plan.append(
            {
                "action_id": row["action_id"],
                "stage_id": row["stage_id"],
                "stage_index": row["stage_index"],
                "tooth_number": row.get("tooth_number"),
                "service_title": row.get("work_title"),
                "doctor_name": _doctor_name(row),
                "reservation_date": _json_value(row.get("reservation_date")),
                "reservation_start_time": _json_value(row.get("reservation_start_time")),
                "reservation_end_time": _json_value(row.get("reservation_end_time")),
                "estimated_duration_days": row.get("estimated_duration_days"),
                "estimated_duration_label": _duration_label(row.get("estimated_duration_days")),
                "price": _json_value(row.get("action_price") or 0),
                "is_done": row.get("action_is_done"),
                "is_paid": row.get("action_is_paid"),
            }
        )

    data.update(
        {
            "client": {"client_id": card.get("client_id")},
            "stage": list(stages.values()),
            "credits": [],
            "transactions": await _transactions(card["card_id"]),
            "treatment_plan": treatment_plan,
            "card_title": f"Davolanish kartasi {data['card_number']}",
            "contract_link": None,
        }
    )
    return data


async def _transactions(card_id: int) -> list[dict[str, Any]]:
    try:
        rows = await CRM_DB.fetch(
            """
            SELECT transaction_id, transaction_type, transaction_payment_type,
                   transaction_sum, comment, transaction_created_at
            FROM transaction_transaction
            WHERE transaction_card_id = $1
            ORDER BY transaction_created_at DESC
            """,
            card_id,
        )
    except UndefinedTableError:
        return []
    return [
        {key: _json_value(value) for key, value in dict(row).items()}
        for row in rows
    ]


async def list_treatments(
    auth_user: dict[str, Any],
    *,
    status: str | None,
    payment_status: str | None,
    page: int | None,
    page_size: int | None,
):
    if demo_account.is_demo_auth(auth_user):
        rows = demo_account.section("treatments", [])
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if payment_status:
            rows = [row for row in rows if row.get("payment_status") == payment_status]
        if page:
            safe_size = max(page_size or 10, 1)
            start = (max(page, 1) - 1) * safe_size
            page_rows = rows[start : start + safe_size]
        else:
            page_rows = rows
        return paginate_rows(page_rows, count=len(rows), page=page, page_size=page_size)

    client_id = auth_user.get("crm_client_id")
    if not client_id:
        return paginate_rows([], count=0, page=page, page_size=page_size)
    offset, limit = offset_limit(page, page_size)
    try:
        count = await CRM_DB.fetchval(
            """
            SELECT COUNT(*)
            FROM medcard_medicalcard
            WHERE client_id = $1
              AND COALESCE(deleted, FALSE) = FALSE
              AND COALESCE(card_is_cancelled, FALSE) = FALSE
            """,
            client_id,
        )
        query = """
            SELECT *
            FROM medcard_medicalcard
            WHERE client_id = $1
              AND COALESCE(deleted, FALSE) = FALSE
              AND COALESCE(card_is_cancelled, FALSE) = FALSE
            ORDER BY card_created_at DESC
        """
        args = [client_id]
        if limit is not None:
            query += " LIMIT $2 OFFSET $3"
            args.extend([limit, offset])
        rows = [dict(row) for row in await CRM_DB.fetch(query, *args)]
    except (UndefinedTableError, UndefinedColumnError):
        return paginate_rows([], count=0, page=page, page_size=page_size)

    data = []
    for row in rows:
        item = await _serialize_card(row)
        if status and item["status"] != status:
            continue
        if payment_status and item["payment_status"] != payment_status:
            continue
        data.append(item)
    return paginate_rows(data, count=count or len(data), page=page, page_size=page_size)


async def active_treatment_count(client_id: int | None) -> int:
    if not client_id:
        return 0
    try:
        return int(
            await CRM_DB.fetchval(
                """
                SELECT COUNT(*)
                FROM medcard_medicalcard
                WHERE client_id = $1
                  AND COALESCE(deleted, FALSE) = FALSE
                  AND COALESCE(card_is_cancelled, FALSE) = FALSE
                  AND COALESCE(card_is_done, FALSE) = FALSE
                """,
                client_id,
            )
            or 0
        )
    except (UndefinedTableError, UndefinedColumnError):
        return 0


async def treatment_detail(auth_user: dict[str, Any], treatment_id: int):
    if demo_account.is_demo_auth(auth_user):
        details = demo_account.section("treatment_details", {})
        detail = details.get(str(treatment_id))
        if detail:
            return detail
        for row in demo_account.section("treatments", []):
            if row.get("card_id") == treatment_id:
                return row
        raise HTTPException(status_code=404, detail="Treatment was not found")

    client_id = auth_user.get("crm_client_id")
    if not client_id:
        raise HTTPException(status_code=404, detail="Treatment was not found")
    try:
        row = await CRM_DB.fetchrow(
            """
            SELECT *
            FROM medcard_medicalcard
            WHERE card_id = $1
              AND client_id = $2
              AND COALESCE(deleted, FALSE) = FALSE
              AND COALESCE(card_is_cancelled, FALSE) = FALSE
            """,
            treatment_id,
            client_id,
        )
    except (UndefinedTableError, UndefinedColumnError):
        row = None
    if not row:
        raise HTTPException(status_code=404, detail="Treatment was not found")
    return await _serialize_card(dict(row), detail=True)
