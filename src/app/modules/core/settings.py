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
        url_str = (
            f"{self.driver}://" +
            (f"{self.username}:{self.password}" if self.username and self.password else "") +
            (f"@{self.host}" if self.host else "") +
            (f":{self.port}" if self.port else "") +
            f"/{self.database_name}"
        )
        return url_str

    model_config = SettingsConfigDict(env_prefix='DB_', extra='allow')