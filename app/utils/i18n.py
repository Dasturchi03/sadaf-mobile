from __future__ import annotations

from contextvars import ContextVar


SUPPORTED_LANGUAGES = ("uz", "ru", "en")
DEFAULT_LANGUAGE = "uz"

_current_language: ContextVar[str] = ContextVar(
    "_current_language",
    default=DEFAULT_LANGUAGE,
)


def normalize_language(value: str | None) -> str:
    language = (value or DEFAULT_LANGUAGE).strip().lower()
    if "-" in language:
        language = language.split("-", 1)[0]
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    return _current_language.get()


def set_language(value: str | None):
    return _current_language.set(normalize_language(value))


def reset_language(token) -> None:
    _current_language.reset(token)


def localized(values: dict[str, str], default: str | None = None) -> str:
    language = get_language()
    if language in values:
        return values[language]
    if DEFAULT_LANGUAGE in values:
        return values[DEFAULT_LANGUAGE]
    return default or next(iter(values.values()))
