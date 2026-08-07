from __future__ import annotations

import json
from math import ceil
from typing import Any
from urllib.parse import quote

import asyncpg
from fastapi import HTTPException

from app.core.config import settings
from app.utils.i18n import get_language


def lang_suffix() -> str:
    return get_language()


def as_dict(row: asyncpg.Record | None) -> dict | None:
    return normalize_json_values(dict(row)) if row else None


def as_list(rows: list[asyncpg.Record]) -> list[dict]:
    return [normalize_json_values(dict(row)) for row in rows]


def normalize_json_values(data: dict) -> dict:
    normalized = {}
    for key, value in data.items():
        if isinstance(value, str) and value[:1] in {"[", "{"}:
            try:
                normalized[key] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
        normalized[key] = value
    return normalized


def paginate_rows(
    rows: list[dict],
    *,
    count: int,
    page: int | None,
    page_size: int | None,
) -> list[dict] | dict[str, Any]:
    if not page:
        return rows

    page_size = page_size or 10
    pages = ceil(count / page_size) if page_size else 1
    return {
        "count": count,
        "next": page + 1 if page < pages else None,
        "previous": page - 1 if page > 1 else None,
        "results": rows,
    }


def offset_limit(page: int | None, page_size: int | None) -> tuple[int | None, int | None]:
    if not page:
        return None, None
    safe_page = max(page, 1)
    safe_size = max(page_size or 10, 1)
    return (safe_page - 1) * safe_size, safe_size


def not_found(detail: str):
    raise HTTPException(status_code=404, detail=detail)


def crm_media_url(value: str | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith(("http://", "https://")):
        return raw

    base = (settings.CRM_MEDIA_BASE_URL or "https://api.sadaf-clinic.uz/media").strip()
    if not base.startswith(("http://", "https://")):
        base = f"https://{base}"
    base = base.rstrip("/")
    if not base.endswith("/media"):
        base = f"{base}/media"

    path = raw.lstrip("/")
    if path.startswith("media/"):
        path = path[len("media/"):]
    return f"{base}/{quote(path, safe='/')}"
