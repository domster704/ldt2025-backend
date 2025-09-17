from pydantic_settings import BaseSettings, SettingsConfigDict


class KeycloakSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8', extra='ignore', env_prefix='KC_'
    )

    issuer: str
    client_id: str
    client_secret: str | None = None
    redirect_uri: str | None = None
    scopes: str | None = None
    jwks_ttl: int = 300