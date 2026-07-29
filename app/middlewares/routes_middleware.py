from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.app.base_url_store import set_base_url_once


class CaptureBaseUrlOnceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        set_base_url_once(str(request.base_url))
        return await call_next(request)
