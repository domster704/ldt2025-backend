from app.modules.auth.domain.entities import Tokens
from app.modules.auth.domain.interfaces import AuthProvider
from app.modules.auth.domain.value_objects import RefreshToken


async def refresh_tokens(provider: AuthProvider, refresh_token: str) -> Tokens:
    return await provider.refresh(RefreshToken(refresh_token))
