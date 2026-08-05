from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.mobile.deps import body_or_form, body_or_form_openapi
from app.api.mobile import schemas as sc
from app.services.mobile import (
    accounts,
    content,
    crm_catalog,
    notifications,
    reservation_requests,
    reservations,
    treatments,
)
from app.utils.deps.auth import Auth


router = APIRouter(tags=["Mobile"])

MobileOTPRequestBody = Annotated[sc.MobileOTPRequest, Depends(body_or_form(sc.MobileOTPRequest))]
MobileOTPVerifyBody = Annotated[sc.MobileOTPVerify, Depends(body_or_form(sc.MobileOTPVerify))]
MobileOTPRegisterBody = Annotated[
    sc.MobileOTPRegisterRequest,
    Depends(body_or_form(sc.MobileOTPRegisterRequest)),
]
MobileNotificationDeviceBody = Annotated[
    sc.MobileNotificationDeviceRequest,
    Depends(body_or_form(sc.MobileNotificationDeviceRequest)),
]
MobileNotificationTestSendBody = Annotated[
    sc.MobileNotificationTestSendRequest,
    Depends(body_or_form(sc.MobileNotificationTestSendRequest)),
]
PartnerInquiryBody = Annotated[sc.PartnerInquiryRequest, Depends(body_or_form(sc.PartnerInquiryRequest))]
ReservationRequestBody = Annotated[
    sc.MobileReservationRequestCreate,
    Depends(body_or_form(sc.MobileReservationRequestCreate)),
]
ApplyReferralCodeBody = Annotated[
    sc.ApplyReferralCodeRequest,
    Depends(body_or_form(sc.ApplyReferralCodeRequest)),
]
MobileMeUpdateBody = Annotated[sc.MobileMeUpdateRequest, Depends(body_or_form(sc.MobileMeUpdateRequest))]


@router.get("/mobile/me")
async def mobile_me(auth_user: Auth):
    return await accounts.me(auth_user)


@router.put("/mobile/me", openapi_extra=body_or_form_openapi(sc.MobileMeUpdateRequest))
async def mobile_me_update(request: MobileMeUpdateBody, auth_user: Auth):
    return await accounts.update_me(auth_user, request)


@router.get("/mobile/loyalty")
async def mobile_loyalty(auth_user: Auth):
    return await accounts.loyalty(auth_user)


@router.get("/mobile/status")
async def mobile_status(auth_user: Auth):
    return await accounts.status(auth_user)


@router.get("/country_list")
async def country_list():
    return await content.country_list()


@router.get("/mobile/dashboard")
async def mobile_dashboard(auth_user: Auth):
    return await accounts.dashboard(auth_user)


@router.get("/mobile/contacts")
async def mobile_contacts():
    return await content.contacts()


@router.get("/mobile/terms")
async def mobile_terms(_: Auth, text_type: str):
    return await content.terms(text_type=text_type)


@router.get("/mobile/notifications")
async def mobile_notifications(
    auth_user: Auth,
    page: int | None = None,
    page_size: int | None = None,
):
    return await notifications.list_notifications(
        auth_user,
        page=page,
        page_size=page_size,
    )


@router.get("/mobile/vacancies")
async def mobile_vacancies(page: int | None = None, page_size: int | None = None):
    return await content.vacancies(page=page, page_size=page_size)


@router.get("/mobile/vacancies/{id}")
async def mobile_vacancy_detail(id: int):
    return await content.vacancy_detail(vacancy_id=id)


@router.get("/categories")
async def categories(page: int | None = None, page_size: int | None = None):
    return await crm_catalog.categories(page=page, page_size=page_size)


@router.get("/mobile/articles")
async def mobile_articles(
    article_type: str | None = None,
    q: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
):
    return await content.articles(
        article_type=article_type,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/mobile/reservation/doctors")
async def mobile_reservation_doctors(
    specialization: str | None = None,
    category_id: int | None = None,
):
    return await reservations.doctors(
        specialization=specialization,
        category_id=category_id,
    )


@router.get("/mobile/reservation/doctors/{id}")
async def mobile_reservation_doctor_detail(id: int):
    return await reservations.doctor_detail(doctor_id=id)


@router.get("/mobile/reservation/doctors/{id}/slots")
async def mobile_reservation_doctor_slots(
    id: int,
    date: str,
    slot_minutes: int = 60,
):
    return await reservations.doctor_slots(
        doctor_id=id,
        date_value=date,
        slot_minutes=slot_minutes,
    )


@router.get("/mobile/reservation/doctors/{id}/works")
async def mobile_reservation_doctor_works(id: int):
    return await reservations.doctor_works(doctor_id=id)


@router.get("/mobile/reservations")
async def mobile_reservations(
    auth_user: Auth,
    status: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
):
    return await reservations.list_user_reservations(
        auth_user,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/mobile/reservations/{id}")
async def mobile_reservation_detail(id: int, auth_user: Auth):
    return await reservations.user_reservation_detail(auth_user, id)


@router.get("/mobile/treatments")
async def mobile_treatments(
    auth_user: Auth,
    status: str | None = None,
    payment_status: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
):
    return await treatments.list_treatments(
        auth_user,
        status=status,
        payment_status=payment_status,
        page=page,
        page_size=page_size,
    )


@router.get("/mobile/treatments/{id}")
async def mobile_treatment_detail(id: int, auth_user: Auth):
    return await treatments.treatment_detail(auth_user, id)


@router.get("/mobile/contract/download")
async def mobile_contract_download(_: Auth):
    return await content.contract_download()


@router.post("/mobile/auth/otp/request", openapi_extra=body_or_form_openapi(sc.MobileOTPRequest))
async def mobile_otp_request(request: MobileOTPRequestBody):
    return await accounts.otp_request(request)


@router.post("/mobile/auth/otp/verify", openapi_extra=body_or_form_openapi(sc.MobileOTPVerify))
async def mobile_otp_verify(request: MobileOTPVerifyBody):
    return await accounts.otp_verify(request, purpose_hint="login")


@router.post(
    "/mobile/auth/otp/register/request",
    openapi_extra=body_or_form_openapi(sc.MobileOTPRegisterRequest),
)
async def mobile_otp_register_request(request: MobileOTPRegisterBody):
    return await accounts.otp_register_request(request)


@router.post("/mobile/auth/otp/register/verify", openapi_extra=body_or_form_openapi(sc.MobileOTPVerify))
async def mobile_otp_register_verify(request: MobileOTPVerifyBody):
    return await accounts.otp_verify(request, purpose_hint="register")


@router.post(
    "/mobile/notifications/devices/register",
    openapi_extra=body_or_form_openapi(sc.MobileNotificationDeviceRequest),
)
async def mobile_notifications_device_register(
    request: MobileNotificationDeviceBody,
    auth_user: Auth,
):
    return await notifications.register_device(auth_user, request)


@router.post(
    "/mobile/notifications/test/send",
    openapi_extra=body_or_form_openapi(sc.MobileNotificationTestSendRequest),
)
async def mobile_notifications_test_send(
    request: MobileNotificationTestSendBody,
    auth_user: Auth,
):
    return await notifications.test_send_notification(auth_user, request)


@router.post(
    "/mobile/partner-inquiries",
    status_code=201,
    openapi_extra=body_or_form_openapi(sc.PartnerInquiryRequest),
)
async def mobile_partner_inquiries(request: PartnerInquiryBody):
    return await content.partner_inquiry(request)


@router.get("/mobile/reservation-requests")
async def mobile_reservation_requests_list(
    auth_user: Auth,
    page: int | None = None,
    page_size: int | None = None,
):
    return await reservation_requests.list_requests(
        auth_user,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/mobile/reservation-requests",
    status_code=201,
    openapi_extra=body_or_form_openapi(sc.MobileReservationRequestCreate),
)
async def mobile_reservation_requests(request: ReservationRequestBody, auth_user: Auth):
    return await reservation_requests.create_request(auth_user, request)


@router.get("/mobile/reservation-requests/{id}")
async def mobile_reservation_request_detail(id: int, auth_user: Auth):
    return await reservation_requests.detail_request(auth_user, id)


@router.patch("/mobile/reservation-requests/{id}/cancel")
async def mobile_reservation_request_cancel(id: int, auth_user: Auth):
    return await reservation_requests.cancel_request(auth_user, id)


@router.post("/mobile/referral/apply-code", openapi_extra=body_or_form_openapi(sc.ApplyReferralCodeRequest))
async def mobile_referral_apply_code(request: ApplyReferralCodeBody, auth_user: Auth):
    return await accounts.apply_referral_code(auth_user, request)


@router.post("/mobile/vacancies/apply", status_code=201)
async def mobile_vacancies_apply(
    vacancy: int = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    middle_name: str | None = Form(None),
    phone: str = Form(...),
    email: str | None = Form(None),
    address: str | None = Form(None),
    birth_date: str | None = Form(None),
    gender: str | None = Form(None),
    marital_status: str | None = Form(None),
    message: str | None = Form(None),
    resume_file: UploadFile = File(...),
):
    return await content.vacancy_apply(
        vacancy=vacancy,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        phone=phone,
        email=email,
        address=address,
        birth_date=birth_date,
        gender=gender,
        marital_status=marital_status,
        message=message,
        resume_file=resume_file,
    )


@router.patch("/mobile/reservation-requests/{id}/confirm")
async def mobile_reservation_request_confirm(id: int, auth_user: Auth):
    return await reservation_requests.confirm_request(auth_user, id)


@router.patch("/mobile/notifications/{id}/read")
async def mobile_notification_read(id: int, auth_user: Auth):
    return await notifications.read_notification(auth_user, id)


@router.patch("/mobile/notifications/read-all")
async def mobile_notifications_read_all(auth_user: Auth):
    return await notifications.read_all(auth_user)
