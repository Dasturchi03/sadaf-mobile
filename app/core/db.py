from __future__ import annotations

from typing import Optional

import asyncpg
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


mobile_pool: Optional[asyncpg.Pool] = None
crm_pool: Optional[asyncpg.Pool] = None
mobile_engine: Optional[AsyncEngine] = None
mobile_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _sqlalchemy_url(dsn: str) -> str:
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return dsn


async def init_db_pools() -> None:
    global mobile_pool, crm_pool, mobile_engine, mobile_sessionmaker

    if mobile_pool is None:
        mobile_pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
            command_timeout=60,
        )

    if mobile_engine is None:
        mobile_engine = create_async_engine(
            _sqlalchemy_url(settings.DATABASE_URL),
            pool_size=settings.DB_POOL_MIN_SIZE,
            max_overflow=max(settings.DB_POOL_MAX_SIZE - settings.DB_POOL_MIN_SIZE, 0),
            pool_pre_ping=True,
        )
        mobile_sessionmaker = async_sessionmaker(
            bind=mobile_engine,
            expire_on_commit=False,
            autoflush=False,
        )

    if crm_pool is None:
        crm_pool = await asyncpg.create_pool(
            dsn=settings.CRM_DATABASE_URL,
            min_size=settings.CRM_DB_POOL_MIN_SIZE,
            max_size=settings.CRM_DB_POOL_MAX_SIZE,
            command_timeout=60,
        )


async def close_db_pools() -> None:
    global mobile_pool, crm_pool, mobile_engine, mobile_sessionmaker

    if mobile_engine is not None:
        await mobile_engine.dispose()
        mobile_engine = None
        mobile_sessionmaker = None

    if mobile_pool is not None:
        await mobile_pool.close()
        mobile_pool = None

    if crm_pool is not None:
        await crm_pool.close()
        crm_pool = None


def get_mobile_pool() -> asyncpg.Pool:
    if mobile_pool is None:
        raise RuntimeError("Mobile DB pool is not initialized")
    return mobile_pool


def get_crm_pool() -> asyncpg.Pool:
    if crm_pool is None:
        raise RuntimeError("CRM DB pool is not initialized")
    return crm_pool


def get_mobile_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if mobile_sessionmaker is None:
        raise RuntimeError("Mobile ORM sessionmaker is not initialized")
    return mobile_sessionmaker
