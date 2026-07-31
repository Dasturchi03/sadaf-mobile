from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sadaf Mobile API"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    DATABASE_URL: str = Field(default='')

    CRM_POSTGRES_USER: str
    CRM_POSTGRES_PASSWORD: str
    CRM_POSTGRES_DB: str
    CRM_POSTGRES_HOST: str
    CRM_POSTGRES_PORT: str
    CRM_DATABASE_URL: str = Field(default='')

    DB_POOL_MIN_SIZE: int = 1
    DB_POOL_MAX_SIZE: int = 20
    CRM_DB_POOL_MIN_SIZE: int = 1
    CRM_DB_POOL_MAX_SIZE: int = 10
    AUTO_RUN_MIGRATIONS: bool = True

    PHONE_PATTERN: str = r"^\+998\d{9}$"
    MOBILE_OTP_EXPIRE_MINUTES: int = 5
    MOBILE_OTP_COOLDOWN_SECONDS: int = 60
    MOBILE_OTP_HOURLY_LIMIT: int = 5
    MOBILE_OTP_VERIFY_MAX_ATTEMPTS: int = 5
    MOBILE_OTP_USE_TEST_CODE: bool = False
    MOBILE_OTP_TEST_CODE: str = "1111"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    SMS_PROVIDER_URL: str = ""
    SMS_PROVIDER_LOGIN: str = ""
    SMS_PROVIDER_PASSWORD: str = ""
    SMS_PROVIDER_SENDER: str = ""
    SMS_PROVIDER_TIMEOUT_SECONDS: int = 10
    SMS_PROVIDER_TTL_SECONDS: int = 300
    SMS_PROVIDER_MESSAGE_ID_PREFIX: str = "sdf"
    SMS_ANDROID_APP_HASH: str = "wv349hp3s0f9"
    SMS_OTP_REGISTER_TEMPLATE_UZ: str = (
        "SADAF ilovasida ro'yxatdan o'tishni tasdiqlash kodi: {code}. "
        "Kodni hech kimga bermang. {app_hash}"
    )
    SMS_OTP_REGISTER_TEMPLATE_RU: str = (
        "Код подтверждения регистрации в приложении SADAF: {code}. "
        "Никому не сообщайте код. {app_hash}"
    )
    SMS_OTP_REGISTER_TEMPLATE_EN: str = (
        "SADAF app registration confirmation code: {code}. "
        "Do not share this code. {app_hash}"
    )
    SMS_OTP_LOGIN_TEMPLATE_UZ: str = (
        "SADAF ilovasiga kirishni tasdiqlash kodi: {code}. "
        "Kodni hech kimga bermang. {app_hash}"
    )
    SMS_OTP_LOGIN_TEMPLATE_RU: str = (
        "Код подтверждения входа в приложение SADAF: {code}. "
        "Никому не сообщайте код. {app_hash}"
    )
    SMS_OTP_LOGIN_TEMPLATE_EN: str = (
        "SADAF app login confirmation code: {code}. "
        "Do not share this code. {app_hash}"
    )
    SMS_OTP_PHONE_CONFIRM_TEMPLATE_UZ: str = (
        "SADAF ilovasida telefon raqamni tasdiqlash kodi: {code}. "
        "Kodni hech kimga bermang. {app_hash}"
    )
    SMS_OTP_PHONE_CONFIRM_TEMPLATE_RU: str = (
        "Код подтверждения номера телефона в приложении SADAF: {code}. "
        "Никому не сообщайте код. {app_hash}"
    )
    SMS_OTP_PHONE_CONFIRM_TEMPLATE_EN: str = (
        "SADAF app phone confirmation code: {code}. "
        "Do not share this code. {app_hash}"
    )
    SMS_OTP_PASSWORD_RESET_TEMPLATE_UZ: str = (
        "SADAF ilovasida parolni tiklashni tasdiqlash kodi: {code}. "
        "Kodni hech kimga bermang. {app_hash}"
    )
    SMS_OTP_PASSWORD_RESET_TEMPLATE_RU: str = (
        "Код подтверждения восстановления пароля в приложении SADAF: {code}. "
        "Никому не сообщайте код. {app_hash}"
    )
    SMS_OTP_PASSWORD_RESET_TEMPLATE_EN: str = (
        "SADAF app password reset confirmation code: {code}. "
        "Do not share this code. {app_hash}"
    )

    MINIO_BUCKETNAME: str = "hardcollection"
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_TAG: str = 'miniofile'

    HTTP_PROXY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None
    CRM_MEDIA_ROOT: Optional[str] = None
    CRM_MEDIA_BASE_URL: Optional[str] = None
    FIREBASE_CREDENTIALS_FILE: Optional[str] = None

    DEBUG: bool = True
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra='allow')

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
        return value

    @field_validator("HTTP_PROXY", "HTTPS_PROXY", mode="before")
    @classmethod
    def normalize_proxy(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    def model_post_init(self, __context):
        self.DATABASE_URL = (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        self.CRM_DATABASE_URL = (
            f"postgresql://{self.CRM_POSTGRES_USER}:{self.CRM_POSTGRES_PASSWORD}"
            f"@{self.CRM_POSTGRES_HOST}:{self.CRM_POSTGRES_PORT}/{self.CRM_POSTGRES_DB}"
        )

settings = Settings()
