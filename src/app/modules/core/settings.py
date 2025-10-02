import functools

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    driver: str
    database_name: str
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None

    @functools.cached_property
    def db_url(self) -> str:
        if self.driver.startswith("sqlite"):
            return f"{self.driver}:///{self.database_name}"

        return (
            f"{self.driver}://{self.username}:{self.password}"
            f"@{self.host}{f':{self.port}' if self.port else ''}"
            f"/{self.database_name}"
        )

    model_config = SettingsConfigDict(env_prefix='DB_', extra='allow')