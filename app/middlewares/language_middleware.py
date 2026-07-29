from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, reset_language, set_language


class LanguageContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path_language = request.url.path.strip("/").split("/", 1)[0]
        language = path_language if path_language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

        token = set_language(language)
        try:
            response = await call_next(request)
        finally:
            reset_language(token)

        response.headers["Content-Language"] = language
        return response
