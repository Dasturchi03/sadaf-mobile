import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from app.api.auth.schemas import user_auth as sc
from app.api.auth.services import user_auth as sv
from app.api.mobile.deps import body_or_form, body_or_form_openapi


logger = logging.getLogger(__name__)

router_auth_v1 = APIRouter(prefix = "/v1", tags=["Auth v1"])
login_router = APIRouter(prefix="/users", tags=["Users login"])
router = APIRouter()
UserLoginBody = Annotated[sc.UserLoginRequest, Depends(body_or_form(sc.UserLoginRequest))]


@login_router.post('/login/', openapi_extra=body_or_form_openapi(sc.UserLoginRequest))
async def login_user(request: UserLoginBody):
    return await sv.login_user(request=request)


@router_auth_v1.post('/api/auth/general')
async def router_auth_v1_general_api():
    pass


@router_auth_v1.post('/user/register')
async def user_register_api():
    pass


@router_auth_v1.post('/user/verify-sms')
async def v1_api():
    pass


@router_auth_v1.post('/user/forgot-password')
async def v1_api():
    pass


@router_auth_v1.post('/user/reset-password')
async def v1_api():
    pass


@router_auth_v1.post('/api/auth/logout')
async def v1_api():
    pass


router.include_router(login_router)
router.include_router(router_auth_v1)
