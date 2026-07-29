from __future__ import annotations

from typing import Any, Iterable

import asyncpg
from sqlalchemy import Executable, Result, text
from sqlalchemy.sql import Delete, Insert, Select, Update

from app.utils.di.db_ctx import ORMDB


async def _get_one(query: str, params: dict[str, Any] | None = None) -> dict | None:
    return await orm_text_one(query, params)


async def _get_all(query: str, params: dict[str, Any] | None = None) -> list[dict]:
    return await orm_text_all(query, params)


async def _execute(query: str, params: dict[str, Any] | None = None) -> int:
    result = await ORMDB.execute(text(query), params or {})
    return result.rowcount or 0


async def orm_execute(stmt: Executable) -> Result[Any]:
    return await ORMDB.execute(stmt)


async def orm_one(stmt: Select | Insert | Update | Delete) -> dict | None:
    row = (await ORMDB.execute(stmt)).mappings().first()
    return dict(row) if row else None


async def orm_all(stmt: Select) -> list[dict]:
    rows = (await ORMDB.execute(stmt)).mappings().all()
    return [dict(row) for row in rows]


async def orm_scalar(stmt: Select) -> Any:
    return (await ORMDB.execute(stmt)).scalar()


async def orm_text_one(query: str, params: dict[str, Any] | None = None) -> dict | None:
    row = (await ORMDB.execute(text(query), params or {})).mappings().first()
    return dict(row) if row else None


async def orm_text_all(query: str, params: dict[str, Any] | None = None) -> list[dict]:
    rows = (await ORMDB.execute(text(query), params or {})).mappings().all()
    return [dict(row) for row in rows]


def records_to_dicts(rows: Iterable[asyncpg.Record]) -> list[dict]:
    return [dict(row) for row in rows]
