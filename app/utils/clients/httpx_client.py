import httpx
from httpx import Limits, AsyncHTTPTransport, Timeout

from app.core.config import settings


_client: httpx.AsyncClient | None = None
_proxy_client: httpx.AsyncClient | None = None


def _proxy_mounts() -> dict[str, AsyncHTTPTransport]:
    mounts: dict[str, AsyncHTTPTransport] = {}
    if settings.HTTP_PROXY:
        mounts["http://"] = AsyncHTTPTransport(proxy=settings.HTTP_PROXY)
    if settings.HTTPS_PROXY:
        mounts["https://"] = AsyncHTTPTransport(proxy=settings.HTTPS_PROXY)
    return mounts


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0),
            limits=Limits(max_connections=100, max_keepalive_connections=20),
            follow_redirects=True,
            trust_env=False,
        )

    return _client


def get_proxy_client() -> httpx.AsyncClient:
    global _proxy_client
    if _proxy_client is None:
        _proxy_client = httpx.AsyncClient(
            mounts=_proxy_mounts(),
            timeout=Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0),
            limits=Limits(max_connections=100, max_keepalive_connections=20),
            follow_redirects=True,
            trust_env=False,
        )

    return _proxy_client


async def aclose_clients():
    global _client, _proxy_client
    if _client is not None:
        await _client.aclose()
        _client = None
    if _proxy_client is not None:
        await _proxy_client.aclose()
        _proxy_client = None
