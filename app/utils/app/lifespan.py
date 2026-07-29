import os, fcntl
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import close_db_pools, init_db_pools


LOCK_PATH = "/tmp/app_scheduler.lock"


def try_acquire_lock():
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError:
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    # from app.utils.scheduler.aps import scheduler, INTERVAL_JOBS
    from app.utils.clients import httpx_client, redis_client

    is_leader_env = os.getenv('IS_LEADER')
    lock_fd = None

    if is_leader_env == '1':
        is_leader = True
    elif is_leader_env == '0':
        is_leader = False
    else:
        lock_fd = try_acquire_lock()
        is_leader = lock_fd is not None

    await init_db_pools()

    if settings.AUTO_RUN_MIGRATIONS:
        from app.db.init_db import run_migrations

        await run_migrations()

    # app.state.httpx_client = httpx_client.get_client()
    # app.state.httpx_proxy_client = httpx_client.get_proxy_client()

    # app.state.redis_client = redis_client.get_client()

    # app.state.minio_client = minio_client.get_client()

    # if is_leader:
    #     scheduler.start()
    #     for job in INTERVAL_JOBS:
    #         scheduler.add_job(job, 'interval', days=1)

    try:
        yield
    finally:
        # if is_leader:
        #     scheduler.shutdown()

        if lock_fd:
            os.close(lock_fd)

        await close_db_pools()

        await httpx_client.aclose_clients()
        await redis_client.aclose_client()
