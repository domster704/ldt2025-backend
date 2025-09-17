from app.modules.auth.domain.interfaces import AuthProvider, UserRepository
from app.modules.auth.domain.entities import Tokens
from app.modules.auth.domain.value_objects import AccessToken

async def login_with_code(provider: AuthProvider, users: UserRepository, code: str) -> Tokens:
    tokens = await provider.exchange_code(code)
    claims = await provider.verify(AccessToken(tokens.access_token))
    await users.upsert_from_claims(claims)
    return tokens