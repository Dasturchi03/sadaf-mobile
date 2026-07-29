from __future__ import annotations

import re
from pathlib import Path

from asyncpg import UndefinedTableError
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import insert

from app.api.mobile import schemas as sc
from app.core.config import settings
from app.models.mobile import MobileEvent, PartnerInquiry, VacancyApplication
from app.services.common import db_common as db
from app.services.mobile.common import as_dict, as_list, lang_suffix, not_found, offset_limit, paginate_rows
from app.utils.di.db_ctx import CRM_DB


partner_inquiries_t = PartnerInquiry.__table__
vacancy_applications_t = VacancyApplication.__table__
events_t = MobileEvent.__table__


COUNTRIES = [
    {"name": "Uzbekistan", "code": "UZ"},
    {"name": "Russia", "code": "RU"},
    {"name": "Kazakhstan", "code": "KZ"},
    {"name": "Tajikistan", "code": "TJ"},
    {"name": "Kyrgyzstan", "code": "KG"},
    {"name": "Afghanistan", "code": "AF"},
]


async def country_list():
    return COUNTRIES


async def contacts():
    try:
        row = await CRM_DB.fetchrow(
            """
            SELECT data_id, address, location_latt, location_long, phone,
                   telegram, facebook, instagram, youtube
            FROM about_contacts
            ORDER BY created_at DESC, data_id DESC
            LIMIT 1
            """
        )
    except UndefinedTableError:
        row = None
    if not row:
        not_found("Contacts not found!")
    return as_dict(row)


async def terms(text_type: str):
    lang = lang_suffix()
    try:
        row = await CRM_DB.fetchrow(
            f"""
            SELECT
                   title,
                   COALESCE(to_jsonb(t)->>'text_{lang}', text) AS text,
                   to_jsonb(t)->>'text_ru' AS text_ru,
                   to_jsonb(t)->>'text_en' AS text_en,
                   to_jsonb(t)->>'text_uz' AS text_uz,
                   text_type,
                   text_type AS text_type_display
            FROM about_termsandconditions
            AS t
            WHERE is_active = TRUE AND text_type = $1
            ORDER BY created_at DESC, text_id DESC
            LIMIT 1
            """,
            text_type,
        )
    except UndefinedTableError:
        row = None
    if not row:
        not_found("Active document was not found")
    return as_dict(row)


async def articles(
    article_type: str | None = None,
    q: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
):
    lang = lang_suffix()
    offset, limit = offset_limit(page, page_size)
    where = []
    args = []
    if article_type:
        args.append(article_type)
        where.append(f"a.article_type = ${len(args)}")
    if q:
        args.append(f"%{q}%")
        where.append(f"COALESCE(to_jsonb(a)->>'article_title_{lang}', a.article_title) ILIKE ${len(args)}")
    where_sql = "WHERE " + " AND ".join(where) if where else ""

    try:
        count = await CRM_DB.fetchval(
            f"SELECT count(*) FROM about_article a {where_sql}",
            *args,
        )
        query = f"""
            SELECT
                a.article_id,
                a.article_type,
                a.article_type AS article_type_display,
                COALESCE(to_jsonb(a)->>'article_title_{lang}', a.article_title) AS article_title,
                to_jsonb(a)->>'article_title_ru' AS article_title_ru,
                to_jsonb(a)->>'article_title_en' AS article_title_en,
                to_jsonb(a)->>'article_title_uz' AS article_title_uz,
                COALESCE(to_jsonb(a)->>'article_body_{lang}', a.article_body) AS article_body,
                to_jsonb(a)->>'article_body_ru' AS article_body_ru,
                to_jsonb(a)->>'article_body_en' AS article_body_en,
                to_jsonb(a)->>'article_body_uz' AS article_body_uz,
                (
                    SELECT ai.article_image
                    FROM about_articleimage ai
                    WHERE ai.article_id = a.article_id
                    ORDER BY ai.photo_id
                    LIMIT 1
                ) AS cover_image,
                a.created_at
            FROM about_article a
            {where_sql}
            ORDER BY a.created_at DESC
        """
        if limit is not None:
            args.extend([limit, offset])
            query += f" LIMIT ${len(args) - 1} OFFSET ${len(args)}"
        rows = as_list(await CRM_DB.fetch(query, *args))
    except UndefinedTableError:
        count = 0
        rows = []

    return paginate_rows(rows, count=count or 0, page=page, page_size=page_size)


async def vacancies(page: int | None = None, page_size: int | None = None):
    lang = lang_suffix()
    offset, limit = offset_limit(page, page_size)
    try:
        count = await CRM_DB.fetchval(
            "SELECT count(*) FROM vacancies_vacancy WHERE is_active = TRUE"
        )
        query = f"""
            SELECT vacancy_id,
                   COALESCE(to_jsonb(v)->>'title_{lang}', title) AS title,
                   to_jsonb(v)->>'title_ru' AS title_ru,
                   to_jsonb(v)->>'title_en' AS title_en,
                   to_jsonb(v)->>'title_uz' AS title_uz,
                   COALESCE(to_jsonb(v)->>'description_{lang}', description) AS description,
                   to_jsonb(v)->>'description_ru' AS description_ru,
                   to_jsonb(v)->>'description_en' AS description_en,
                   to_jsonb(v)->>'description_uz' AS description_uz,
                   salary_from, salary_to,
                   address, phone, email, deadline, is_active, sort_order
            FROM vacancies_vacancy
            AS v
            WHERE is_active = TRUE
            ORDER BY sort_order, created_at DESC
        """
        args = []
        if limit is not None:
            query += " LIMIT $1 OFFSET $2"
            args = [limit, offset]
        rows = as_list(await CRM_DB.fetch(query, *args))
    except UndefinedTableError:
        count = 0
        rows = []
    return paginate_rows(rows, count=count or 0, page=page, page_size=page_size)


async def vacancy_detail(vacancy_id: int):
    lang = lang_suffix()
    try:
        row = await CRM_DB.fetchrow(
            f"""
            SELECT vacancy_id,
                   COALESCE(to_jsonb(v)->>'title_{lang}', title) AS title,
                   to_jsonb(v)->>'title_ru' AS title_ru,
                   to_jsonb(v)->>'title_en' AS title_en,
                   to_jsonb(v)->>'title_uz' AS title_uz,
                   COALESCE(to_jsonb(v)->>'description_{lang}', description) AS description,
                   to_jsonb(v)->>'description_ru' AS description_ru,
                   to_jsonb(v)->>'description_en' AS description_en,
                   to_jsonb(v)->>'description_uz' AS description_uz,
                   COALESCE(to_jsonb(v)->>'requirements_{lang}', requirements) AS requirements,
                   COALESCE(to_jsonb(v)->>'responsibilities_{lang}', responsibilities) AS responsibilities,
                   COALESCE(to_jsonb(v)->>'conditions_{lang}', conditions) AS conditions,
                   salary_from, salary_to, address, phone, email,
                   deadline, is_active, sort_order, updated_at, created_at
            FROM vacancies_vacancy
            AS v
            WHERE vacancy_id = $1 AND is_active = TRUE
            """,
            vacancy_id,
        )
    except UndefinedTableError:
        row = None
    if not row:
        not_found("Vacancy not found")
    return as_dict(row)


def _normalize_phone(phone: str) -> str:
    phone_number = phone.strip()
    if not re.match(settings.PHONE_PATTERN, phone_number):
        raise HTTPException(
            status_code=400,
            detail={"phone": "Phone number pattern example: +998901234567"},
        )
    return phone_number


async def partner_inquiry(request: sc.PartnerInquiryRequest):
    row = await db.orm_one(
        insert(partner_inquiries_t)
        .values(
            full_name=request.full_name,
            phone=_normalize_phone(request.phone),
            email=str(request.email) if request.email else None,
            message=request.message,
        )
        .returning(
            partner_inquiries_t.c.inquiry_id,
            partner_inquiries_t.c.full_name,
            partner_inquiries_t.c.phone,
            partner_inquiries_t.c.email,
            partner_inquiries_t.c.message,
            partner_inquiries_t.c.created_at,
            partner_inquiries_t.c.updated_at,
        )
    )
    return row


async def vacancy_apply(
    *,
    vacancy: int,
    first_name: str,
    last_name: str,
    middle_name: str | None = None,
    phone: str,
    email: str | None = None,
    address: str | None = None,
    birth_date: str | None = None,
    gender: str | None = None,
    marital_status: str | None = None,
    message: str | None = None,
    resume_file: UploadFile,
):
    await vacancy_detail(vacancy)
    upload_root = Path("uploads/vacancies")
    upload_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(resume_file.filename or "resume").name
    extension = Path(safe_name).suffix.lower().lstrip(".")
    if extension not in {"pdf", "doc", "docx"}:
        raise HTTPException(
            status_code=400,
            detail={"resume_file": "Allowed file types: pdf, doc, docx"},
        )
    target = upload_root / f"{vacancy}_{safe_name}"
    content = await resume_file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail={"resume_file": "Maximum file size is 10 MB"},
        )
    parsed_birth_date = sc.parse_mobile_date(birth_date) if birth_date else None
    if birth_date and parsed_birth_date == birth_date:
        raise HTTPException(
            status_code=400,
            detail={"birth_date": "Date format must be DD-MM-YYYY or YYYY-MM-DD"},
        )
    target.write_bytes(content)
    row = await db.orm_one(
        insert(vacancy_applications_t)
        .values(
            crm_vacancy_id=vacancy,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            phone=_normalize_phone(phone),
            email=email,
            address=address,
            birth_date=parsed_birth_date,
            gender=gender,
            marital_status=marital_status,
            message=message,
            resume_file_path=str(target),
        )
        .returning(
            vacancy_applications_t.c.application_id,
            vacancy_applications_t.c.crm_vacancy_id,
            vacancy_applications_t.c.first_name,
            vacancy_applications_t.c.last_name,
            vacancy_applications_t.c.phone,
            vacancy_applications_t.c.middle_name,
            vacancy_applications_t.c.email,
            vacancy_applications_t.c.address,
            vacancy_applications_t.c.birth_date,
            vacancy_applications_t.c.gender,
            vacancy_applications_t.c.marital_status,
            vacancy_applications_t.c.message,
            vacancy_applications_t.c.resume_file_path,
            vacancy_applications_t.c.status,
            vacancy_applications_t.c.created_at,
            vacancy_applications_t.c.updated_at,
        )
    )
    await db.orm_execute(
        insert(events_t).values(
            event_type="vacancy_application.created",
            aggregate_type="vacancy_application",
            aggregate_id=str(row["application_id"]),
            payload={
                "application_id": row["application_id"],
                "crm_vacancy_id": vacancy,
                "phone": phone,
            },
        )
    )
    return row


async def contract_download():
    try:
        row = await CRM_DB.fetchrow(
            """
            SELECT contract_id, file
            FROM about_contractdocument
            WHERE is_active = TRUE
            ORDER BY created_at DESC, contract_id DESC
            LIMIT 1
            """
        )
    except UndefinedTableError:
        row = None
    if not row or not row["file"]:
        not_found("Active document was not found")

    file_name = row["file"]
    if settings.CRM_MEDIA_ROOT:
        path = Path(settings.CRM_MEDIA_ROOT) / file_name
        if path.exists():
            return FileResponse(
                path,
                media_type="application/pdf",
                filename=path.name,
            )

    if settings.CRM_MEDIA_BASE_URL:
        return RedirectResponse(
            f"{settings.CRM_MEDIA_BASE_URL.rstrip('/')}/{file_name.lstrip('/')}"
        )

    raise HTTPException(
        status_code=404,
        detail="Contract file storage is not configured",
    )
