import functools

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    driver: str
    host: str
    port: int | None = None
    username: str
    password: str
    database_name: str
    echo: bool = False

    @functools.cached_property
    def db_url(self) -> str:
        return (
            f"{self.driver}://{self.username}:"
            f"{self.password}@{self.host}"
            f"{f':{self.port}' if self.port else ''}"
            f"/{self.database_name}"
        )

    model_config = SettingsConfigDict(env_prefix='DB_', extra='allow')