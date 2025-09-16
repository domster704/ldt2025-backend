from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class JWTSettings(BaseSettings):
    secret: SecretStr = Field(..., min_length=32)
    ttl_minutes: int = 14 * 24 * 60
    algorithm: str = "HS256"


class GoogleSettings(BaseSettings):
    credentials_file: str = "token.json"


class TelegramSettings(BaseSettings):
    token: SecretStr = Field(...)


class SecuritySettings(BaseSettings):
    secretkey: SecretStr = Field(...)
    apikeys: list[str] = Field(...)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
        env_prefix="",
        extra="forbid",
        env_nested_delimiter="_",
    )

    debug: bool = False
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    bot: TelegramSettings = Field(default_factory=TelegramSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)


settings = Settings()
