from app.modules.auth.domain.interfaces import TokenVerifier
from app.modules.auth.domain.value_objects import AccessToken


async def verify_access(token_verifier: TokenVerifier, access_token: str) -> dict:
    return await token_verifier(AccessToken(access_token))
