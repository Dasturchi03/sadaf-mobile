from minio import Minio, S3Error
from app.core.config import settings


_client: Minio | None = None


def get_client():
    global _client

    _client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False
    )

    return _client


def make_buckets():
    global _client
    if not _client.bucket_exists(settings.MINIO_BUCKETNAME):
        _client.make_bucket(settings.MINIO_BUCKETNAME)
