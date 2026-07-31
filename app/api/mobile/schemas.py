from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, field_validator


def parse_mobile_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return value


def parse_mobile_time(value):
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    return value


class MobileOTPRequest(BaseModel):
    phone_number: str


class MobileOTPVerify(MobileOTPRequest):
    otp_code: str


class MobileOTPRegisterRequest(MobileOTPRequest):
    client_firstname: str
    client_lastname: str
    client_father_name: str | None = None
    client_birthdate: date
    client_gender: str
    client_citizenship: str
    client_address: str | None = None
    client_telegram: str | None = None

    @field_validator("client_birthdate", mode="before")
    @classmethod
    def parse_birthdate(cls, value):
        return parse_mobile_date(value)


class MobileNotificationDeviceRequest(BaseModel):
    token: str
    platform: str = "unknown"
    device_uid: str | None = None


class MobileNotificationTestSendRequest(BaseModel):
    username: str
    message: str


class PartnerInquiryRequest(BaseModel):
    full_name: str
    phone: str
    email: EmailStr | None = None
    message: str


class MobileReservationRequestCreate(BaseModel):
    flutter_reservation_id: str | None = None
    doctor_id: int
    reservation_work_id: int
    note: str | None = None
    date: date
    time: time
    slot_minutes: int = 60

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value):
        return parse_mobile_date(value)

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, value):
        return parse_mobile_time(value)


class MobileMeUpdateRequest(BaseModel):
    client_firstname: str | None = None
    client_lastname: str | None = None
    client_father_name: str | None = None
    client_birthdate: date | None = None
    client_gender: str | None = None
    client_citizenship: str | None = None
    client_address: str | None = None
    client_telegram: str | None = None
    note: str | None = None
    phone: str | None = None

    @field_validator("client_birthdate", mode="before")
    @classmethod
    def parse_birthdate(cls, value):
        return parse_mobile_date(value)


class ApplyReferralCodeRequest(BaseModel):
    referral_code: str
