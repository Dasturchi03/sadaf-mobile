from typing import Any
from fastapi import HTTPException


class NotFoundError(HTTPException):
    def __init__(self, detail: Any = "Ma'lumot topilmadi", headers: dict = None):
        super().__init__(status_code=404, detail=detail, headers=headers)


class PermissionDenied(HTTPException):
    def __init__(self, detail: Any = "Ruxsat berilmagan"):
        super().__init__(status_code=403, detail=detail)


class BadRequest(HTTPException):
    def __init__(self, detail: Any = "So‘rovda xatolik"):
        super().__init__(status_code=400, detail=detail)


class DataBaseError(HTTPException):
    def __init__(self, detail: Any = "Ma'lumotlar bazasida xatolik", headers = None):
        super().__init__(400, detail, headers)


class ValidationFailed(HTTPException):
    def __init__(self, detail: Any = "Validation failed!"):
        super().__init__(422, detail=detail)


class RequestFailed(HTTPException):
    def __init__(self, detail: str):
        "Request exception class"
        super().__init__(200, detail = {"message": "Tashqi apidan ma'lumotlarni olishda xatolik!",
                                        "data": detail})
