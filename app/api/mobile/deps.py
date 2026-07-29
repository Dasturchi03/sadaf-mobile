from __future__ import annotations

from typing import TypeVar

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError


ModelT = TypeVar("ModelT", bound=BaseModel)


def body_or_form(model_class: type[ModelT]):
    async def parse(request: Request) -> ModelT:
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        try:
            if content_type in {"multipart/form-data", "application/x-www-form-urlencoded"}:
                form = await request.form()
                data = {key: (None if value == "" else value) for key, value in form.items()}
            else:
                data = await request.json()
        except Exception:
            data = {}

        try:
            return model_class.model_validate(data)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors(), body=data) from exc

    return parse


def body_or_form_openapi(model_class: type[BaseModel], *, required: bool = True):
    schema = model_class.model_json_schema()
    return {
        "requestBody": {
            "required": required,
            "content": {
                "application/json": {"schema": schema},
                "multipart/form-data": {"schema": schema},
                "application/x-www-form-urlencoded": {"schema": schema},
            },
        },
    }
