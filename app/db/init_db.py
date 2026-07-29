from __future__ import annotations

from pathlib import Path

from app.core.db import get_mobile_pool


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


async def run_migrations() -> None:
    pool = get_mobile_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                version = migration.name
                exists = await conn.fetchval(
                    "SELECT 1 FROM schema_migrations WHERE version = $1",
                    version,
                )
                if exists:
                    continue

                await conn.execute(migration.read_text(encoding="utf-8"))
                await conn.execute(
                    "INSERT INTO schema_migrations(version) VALUES ($1)",
                    version,
                )


async def create_db() -> None:
    await run_migrations()
