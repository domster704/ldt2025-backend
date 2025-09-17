from app.modules.auth.domain.interfaces import UserRepository, TokenVerifier
from app.modules.auth.domain.value_objects import AccessToken

async def get_current_user(users: UserRepository, token_verifier: TokenVerifier, access_token: str):
    claims = await token_verifier(AccessToken(access_token))
    sub = claims.get("sub")
    return await users.get_by_sub(sub)