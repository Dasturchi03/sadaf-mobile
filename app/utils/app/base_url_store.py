from typing import Optional
from threading import Lock


_BASE_URL: Optional[str] = None
_LOCK = Lock()


def set_base_url_once(url: str) -> None:
    global _BASE_URL
    if _BASE_URL is None:
        with _LOCK:
            if _BASE_URL is None:
                _BASE_URL = url.rstrip("/") + "/"


def get_base_url() -> str:
    return _BASE_URL if _BASE_URL else ''
