from typing import Annotated
from urllib.parse import urljoin
from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema
from app.utils.app.base_url_store import get_base_url


def _to_internal(v: str) -> str:
    if v is None:
        return v
    s = str(v).strip()
    base = get_base_url()
    if s.startswith(base):
        return s[len(base):]
    if s.startswith("/"):
        s = s[1:]
    return s


def _to_external(v: str) -> str:
    if v is None:
        return v
    s = str(v)
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return urljoin(get_base_url(), s)


FilePath = Annotated[
    str,
    BeforeValidator(_to_internal),
    PlainSerializer(_to_external, return_type=str),
    WithJsonSchema({"type": "string", "format": "uri"})
]
