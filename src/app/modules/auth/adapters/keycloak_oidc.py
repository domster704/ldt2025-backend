import httpx
import jwt
from jwt import PyJWKClient
from typing import Any
from app.modules.auth.domain.entities import Tokens
from app.modules.auth.domain.interfaces import AuthProvider
from app.modules.auth.domain.value_objects import AccessToken, RefreshToken

class KeycloakOIDC(AuthProvider):
    def __init__(self, issuer: str, client_id: str, client_secret: str | None, redirect_uri, timeout: float = 5.0):
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.timeout = timeout
        self._open_id: dict[str, Any] | None = None
        self._jwks_client: PyJWKClient | None = None

    async def _openid(self) -> dict[str, Any]:
        if self._open_id:
            return self._open_id
        url = f"{self.issuer}/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url)
            r.raise_for_status()
            self._open_id = r.json()
            return self._open_id

    async def _jwks(self) -> PyJWKClient:
        if self._jwks_client:
            return self._jwks_client
        conf = await self._openid()
        self._jwks_client = PyJWKClient(conf["jwks_uri"])  # type: ignore[arg-type]
        return self._jwks_client

    async def exchange_code(self, code: str) -> Tokens:
        conf = await self._openid()
        token_endpoint = conf["token_endpoint"]
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
        }
        auth = None
        if self.client_secret:
            auth = (self.client_id, self.client_secret)
            data.pop("client_id", None)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(token_endpoint, data=data, auth=auth)
            r.raise_for_status()
            js = r.json()
            return Tokens(js["access_token"], js.get("refresh_token"), js.get("token_type", "Bearer"), js.get("expires_in"))

    async def refresh(self, token: RefreshToken) -> Tokens:
        conf = await self._openid()
        token_endpoint = conf["token_endpoint"]
        data = {
            "grant_type": "refresh_token",
            "refresh_token": token.value,
            "client_id": self.client_id,
        }
        auth = None
        if self.client_secret:
            auth = (self.client_id, self.client_secret)
            data.pop("client_id", None)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(token_endpoint, data=data, auth=auth)
            r.raise_for_status()
            js = r.json()
            return Tokens(js["access_token"], js.get("refresh_token"), js.get("token_type", "Bearer"), js.get("expires_in"))

    async def logout(self, token: RefreshToken) -> None:
        conf = await self._openid()
        end_session = conf.get("end_session_endpoint") or conf.get("revocation_endpoint")
        if not end_session:
            return
        data = {"client_id": self.client_id, "refresh_token": token.value}
        auth = None
        if self.client_secret:
            auth = (self.client_id, self.client_secret)
            data.pop("client_id", None)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            await client.post(end_session, data=data, auth=auth)

    async def verify(self, token: AccessToken) -> dict:
        conf = await self._openid()
        jwks = await self._jwks()
        key = jwks.get_signing_key_from_jwt(token.value).key
        return jwt.decode(
            token.value, key, algorithms=["RS256", "RS384", "RS512"], audience=self.client_id, issuer=self.issuer
        )