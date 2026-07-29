from typing import Annotated
from fastapi import Request, Depends
from app.utils.service.minio import Minio


async def get_minio_client(request: Request) -> Minio:
    return request.app.state.minio_client


Client = Annotated[Minio, Depends(get_minio_client)]
