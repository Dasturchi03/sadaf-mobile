from __future__ import annotations

import secrets
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException
from redis.exceptions import RedisError

from app.core.config import settings
from app.utils.clients import httpx_client, redis_client
from app.utils.i18n import DEFAULT_LANGUAGE, get_language, normalize_language


logger = logging.getLogger(__name__)

OTP_PURPOSE_LOGIN = "login"
OTP_PURPOSE_REGISTER = "register"
OTP_PURPOSE_PHONE_CONFIRM = "phone_confirm"
OTP_PURPOSE_PASSWORD_RESET = "password_reset"

_OTP_TEMPLATES = {
    OTP_PURPOSE_LOGIN: {
        "uz": "SMS_OTP_LOGIN_TEMPLATE_UZ",
        "ru": "SMS_OTP_LOGIN_TEMPLATE_RU",
        "en": "SMS_OTP_LOGIN_TEMPLATE_EN",
    },
    OTP_PURPOSE_REGISTER: {
        "uz": "SMS_OTP_REGISTER_TEMPLATE_UZ",
        "ru": "SMS_OTP_REGISTER_TEMPLATE_RU",
        "en": "SMS_OTP_REGISTER_TEMPLATE_EN",
    },
    OTP_PURPOSE_PHONE_CONFIRM: {
        "uz": "SMS_OTP_PHONE_CONFIRM_TEMPLATE_UZ",
        "ru": "SMS_OTP_PHONE_CONFIRM_TEMPLATE_RU",
        "en": "SMS_OTP_PHONE_CONFIRM_TEMPLATE_EN",
    },
    OTP_PURPOSE_PASSWORD_RESET: {
        "uz": "SMS_OTP_PASSWORD_RESET_TEMPLATE_UZ",
        "ru": "SMS_OTP_PASSWORD_RESET_TEMPLATE_RU",
        "en": "SMS_OTP_PASSWORD_RESET_TEMPLATE_EN",
    },
}


def _key(purpose: str, phone_number: str, suffix: str) -> str:
    return f"otp:{purpose}:{phone_number}:{suffix}"


async def _ttl(key: str) -> int:
    ttl = await redis_client.get_client().ttl(key)
    return ttl if ttl and ttl > 0 else 0


def _generate_otp_code() -> str:
    if settings.MOBILE_OTP_USE_TEST_CODE:
        return settings.MOBILE_OTP_TEST_CODE
    return f"{secrets.randbelow(1_000_000):06d}"


def _build_message_id() -> str:
    prefix = "".join(
        symbol for symbol in settings.SMS_PROVIDER_MESSAGE_ID_PREFIX.lower()
        if symbol.isalnum()
    )[:6] or "sdf"
    return f"{prefix}{uuid.uuid4().hex[:20 - len(prefix)]}"


def _send_url() -> str:
    url = settings.SMS_PROVIDER_URL
    if url.rstrip("/").endswith("/send"):
        return url
    return urljoin(url.rstrip("/") + "/", "send")


def build_otp_message(code: str, purpose: str, language: str | None = None) -> str:
    normalized_language = normalize_language(language or get_language())
    purpose_templates = _OTP_TEMPLATES.get(purpose)
    if not purpose_templates:
        raise HTTPException(status_code=500, detail=f"Unknown OTP purpose: {purpose}")

    template_name = purpose_templates.get(normalized_language) or purpose_templates[DEFAULT_LANGUAGE]
    template = getattr(settings, template_name)
    return str(template).replace("\\n", "\n").format(
        code=code,
        app_hash=settings.SMS_ANDROID_APP_HASH,
    ).strip()


async def _check_throttle(phone_number: str, purpose: str) -> None:
    client = redis_client.get_client()
    cooldown_key = _key(purpose, phone_number, "cooldown")
    hourly_key = _key(purpose, phone_number, "hourly_count")

    try:
        cooldown_created = await client.set(
            cooldown_key,
            "1",
            nx=True,
            ex=settings.MOBILE_OTP_COOLDOWN_SECONDS,
        )
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is not available for OTP throttling") from exc
    if not cooldown_created:
        raise HTTPException(
            status_code=429,
            detail="OTP was already sent. Try again later.",
            headers={"Retry-After": str(await _ttl(cooldown_key))},
        )

    try:
        sent_count = await client.incr(hourly_key)
        if sent_count == 1:
            await client.expire(hourly_key, 60 * 60)
        if sent_count > settings.MOBILE_OTP_HOURLY_LIMIT:
            await client.delete(cooldown_key)
            raise HTTPException(
                status_code=429,
                detail="Too many OTP requests. Try again later.",
                headers={"Retry-After": str(await _ttl(hourly_key))},
            )

        await client.delete(_key(purpose, phone_number, "verify_attempts"))
    except RedisError as exc:
        try:
            await client.delete(cooldown_key)
        except RedisError:
            pass
        raise HTTPException(status_code=503, detail="Redis is not available for OTP throttling") from exc


async def send_sms(phone_number: str, message: str) -> dict[str, Any]:
    missing = [
        key for key, value in {
            "SMS_PROVIDER_URL": settings.SMS_PROVIDER_URL,
            "SMS_PROVIDER_LOGIN": settings.SMS_PROVIDER_LOGIN,
            "SMS_PROVIDER_PASSWORD": settings.SMS_PROVIDER_PASSWORD,
            "SMS_PROVIDER_SENDER": settings.SMS_PROVIDER_SENDER,
        }.items()
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Missing Playmobile settings: {', '.join(missing)}",
        )

    message_id = _build_message_id()
    payload = {
        "sms": {
            "originator": settings.SMS_PROVIDER_SENDER,
            "ttl": settings.SMS_PROVIDER_TTL_SECONDS,
            "content": {"text": message},
        },
        "messages": [
            {
                "recipient": phone_number.lstrip("+"),
                "message-id": message_id,
            }
        ],
    }
    client = httpx_client.get_client()
    try:
        response = await client.post(
            _send_url(),
            json=payload,
            auth=(settings.SMS_PROVIDER_LOGIN, settings.SMS_PROVIDER_PASSWORD),
            headers={"Content-Type": "application/json; charset=UTF-8"},
            timeout=settings.SMS_PROVIDER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Playmobile returned HTTP {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Playmobile request failed") from exc

    provider_response = response.text.strip()
    logger.info(
        "Playmobile SMS response message_id=%s recipient=%s status_code=%s body=%s",
        message_id,
        phone_number,
        response.status_code,
        provider_response,
    )

    return {
        "message_id": message_id,
        "provider_status_code": response.status_code,
        "provider_response": provider_response,
    }


async def prepare_and_send_otp(phone_number: str, purpose: str) -> tuple[str, datetime, str, dict[str, Any] | None]:
    language = normalize_language(get_language())
    await _check_throttle(phone_number, purpose)
    code = _generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.MOBILE_OTP_EXPIRE_MINUTES)
    if settings.MOBILE_OTP_USE_TEST_CODE:
        return code, expires_at, language, None

    result = await send_sms(phone_number, build_otp_message(code, purpose, language))
    return code, expires_at, language, result
