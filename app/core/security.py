from pydantic_settings import BaseSettings, SettingsConfigDict


class Security(BaseSettings):
    AUTH_SECRET_KEY: str

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='allow')

security = Security()
