from typing import Annotated
from fastapi import Depends
from app.utils.auth.auth import AuthHandler


auth_handler = AuthHandler()

Auth = Annotated[dict, Depends(auth_handler.auth_wrapper)]

auth = Depends(auth_handler.auth_wrapper)
