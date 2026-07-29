import logging
import inspect
import textwrap
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import ResponseValidationError, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.utils.app.lifespan import lifespan
from app.utils.service.minio import get_file
from app.utils.exc import _make_request_id, _format_debug_payload, _snippet_from_endpoint
from app.utils.di import add_db_ctx
from app.middlewares.routes_middleware import CaptureBaseUrlOnceMiddleware
from app.middlewares.language_middleware import LanguageContextMiddleware


logger = logging.getLogger("uvicorn.error")
app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan, docs_url=None)
app.openapi_version = "3.0.0"
app.mount("/swager", StaticFiles(directory="app/utils/swagger"), name="swagger")
app.add_middleware(LanguageContextMiddleware)
app.add_middleware(CaptureBaseUrlOnceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_pagination(app)
add_db_ctx(app)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    rid = _make_request_id(request)
    payload = {"detail": exc.detail}
    headers = {"X-Request-ID": rid}

    if 500 <= exc.status_code < 600:
        logger.exception("HTTPException (5xx) caught", exc_info=exc)

    return JSONResponse(status_code=exc.status_code, content=payload, headers=headers)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    rid = _make_request_id(request)
    payload = {
        "detail": jsonable_encoder(exc.errors()),
        "body": jsonable_encoder(exc.body),
    }
    headers = {"X-Request-ID": rid}
    return JSONResponse(status_code=422, content=payload, headers=headers)


@app.exception_handler(ResponseValidationError)
async def response_validation_handler(request: Request, exc: ResponseValidationError):
    rid = request.headers.get("x-request-id") or ""
    headers = {"X-Request-ID": rid}

    is_coroutine_input = False
    try:
        for err in exc.errors():  # [{'type': ..., 'input': <coroutine ...>}, ...]
            inp = err.get("input")
            if inspect.iscoroutine(inp):
                is_coroutine_input = True
                break
    except Exception:
        pass

    if settings.DEBUG:
        base = {
            "error": "ResponseValidationError",
            "type": exc.__class__.__name__,
            "message": str(exc),
            "root_cause_hint": None,
            "endpoint": {},
        }

        if is_coroutine_input:
            ep = request.scope.get("endpoint")
            ep_info = _snippet_from_endpoint(ep) if ep else None
            hint = (
                "Coroutine returned as response. Probably `await` was forgotten.\n"
            )
            base["root_cause_hint"] = hint
            if ep_info:
                base["endpoint"] = {
                    "file": ep_info["file"],
                    "line_start": ep_info["line_start"],
                    "code_snippet": textwrap.dedent(ep_info["code"])
                }

        logger.exception("ResponseValidationError", exc_info=exc)
        return JSONResponse(status_code=500, content=base, headers=headers)

    logger.exception("ResponseValidationError", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"}, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    rid = _make_request_id(request)
    headers = {"X-Request-ID": rid}

    if settings.DEBUG:
        payload = {"error": "UnhandledException", **_format_debug_payload(exc)}
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(status_code=500, content=payload, headers=headers)

    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"}, headers=headers)


@app.get("/docs", include_in_schema=False)
async def swagger_ui():
    html_resp = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=settings.PROJECT_NAME,
        swagger_js_url="/swager/swagger-ui-bundle.js",
        swagger_css_url="/swager/swagger-ui.css"
    )
    html_str = html_resp.body.decode("utf-8")

    dark_style = '<link rel="stylesheet" href="/swager/swagger-dark.css">'
    html_str = html_str.replace("</head>", f"{dark_style}\n</head>")

    return HTMLResponse(content=html_str, status_code=200)


@app.get(f'/{settings.MINIO_TAG}' + '/{filename}', include_in_schema=False)
async def get_file_from_minio(filename: str):
    return await get_file(filename=filename, inline=True)


@app.get('/', include_in_schema=False, response_class=HTMLResponse)
def core_ui():
    from . import get_project_ui_html
    html = get_project_ui_html(settings.PROJECT_NAME)
    return HTMLResponse(content=html, status_code=200)
