import string
import random
import mimetypes
from urllib.parse import quote
from io import BytesIO
from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from app.core import config
from app.utils.clients.minio_client import Minio, S3Error
from app.utils.exc.exceptions import NotFoundError
from app.utils.di.minio_ctx import minio_client


def make_unique() -> str:
    key = ''.join([random.choice('0123456789' + string.ascii_letters) for _ in range(7)])
    return key


async def save_file(file: UploadFile, client: Minio = None):
    if not client:
        client = minio_client
    if file:
        unique_name = f"{make_unique()}-{file.filename}"
        object_name = f"{config.settings.MINIO_TAG}/{unique_name}"

        file_bytes = await file.read()
        file_stream = BytesIO(file_bytes)

        client.put_object(
            bucket_name=config.settings.MINIO_BUCKETNAME,
            object_name=unique_name,
            data=file_stream,
            length=len(file_bytes),
            content_type=file.content_type or "application/octet-stream"
        )

        return object_name
    else:
        return None


def _build_content_disposition(object_name: str, inline: bool = False) -> str:
    """
    RFC 6266 / 5987: ASCII fallback + UTF-8 filename*
    """
    dispo = "inline" if inline else "attachment"

    ascii_fallback = object_name.encode("ascii", "ignore").decode("ascii").strip()
    if not ascii_fallback:
        ascii_fallback = "file"

    utf8_encoded = quote(object_name, safe="")

    return f"{dispo}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{utf8_encoded}"


async def get_file(filename: str, client: Minio = None, inline: bool = False):
    if not client:
        client = minio_client
    bucket = config.settings.MINIO_BUCKETNAME
    try:
        resp = client.get_object(bucket, filename)
    except S3Error as e:
        raise NotFoundError(detail=f"File not found. {e.message}") from e

    content_disposition = _build_content_disposition(filename, inline=inline)
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    def _close_minio_response():
        try:
            resp.close()
            resp.release_conn()
        except Exception:
            pass

    return StreamingResponse(
        resp,
        media_type=mime,
        headers={"Content-Disposition": content_disposition},
        background=BackgroundTask(_close_minio_response),
    )


def delete_file(path: str, client: Minio = None):
    if not client:
        client = minio_client
    client.remove_object(
        config.settings.MINIO_BUCKETNAME,
        path
    )
