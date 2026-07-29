import uuid
import inspect
import traceback
from typing import Dict, Any
from fastapi import Request
from .exceptions import (NotFoundError as NotFoundError,
                         PermissionDenied as PermissionDenied,
                         BadRequest as BadRequest,
                         DataBaseError as DataBaseError,
                         RequestFailed as RequestFailed,
                         ValidationFailed as ValidationFailed)


def _make_request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def _format_debug_payload(exc: BaseException) -> Dict[str, Any]:
    """
    A very verbose (trace + locals) payload returned in DEBUG mode.
    Note: capture_locals=True may also leak cryptic data.
    """
    tbe = traceback.TracebackException.from_exception(exc, capture_locals=True)
    return {
        "type": exc.__class__.__name__,
        "message": str(exc),
        "frames": [
            {
                "file": f.filename,
                "line": f.lineno,
                "function": f.name,
                "code": f.line,
                "locals": getattr(f, "locals", None),
            }
            for f in reversed(tbe.stack)
        ],
    }


def _snippet_from_endpoint(endpoint, context_lines: int = 12):
    try:
        src_lines, start = inspect.getsourcelines(endpoint)
        src = "".join(src_lines)
        return {"file": inspect.getsourcefile(endpoint), "line_start": start, "code": src}
    except Exception:
        return None
