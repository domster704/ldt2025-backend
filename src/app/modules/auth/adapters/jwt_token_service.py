import jwt
from jwt import PyJWKClient
from app.modules.auth.domain.interfaces import TokenVerifier
from app.modules.auth.domain.value_objects import AccessToken

class JWTTokenService(TokenVerifier):
    def __init__(self, issuer: str, client_id: str):
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.jwks = PyJWKClient(f"{self.issuer}/protocol/openid-connect/certs")

    async def verify(self, token: AccessToken) -> dict:
        key = self.jwks.get_signing_key_from_jwt(token.value).key
        return jwt.decode(token.value, key, algorithms=["RS256", "RS384", "RS512"], audience=self.client_id, issuer=self.issuer)