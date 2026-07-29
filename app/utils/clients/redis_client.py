from redis import asyncio as redis

from app.core.config import settings


_client: redis.Redis | None = None


def get_client():
    global _client
    if _client is None:
        _client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    return _client


async def aclose_client():
    global _client
    if _client is not None:
        await _client.aclose()
