from app.modules.auth.domain.interfaces import AuthProvider
from app.modules.auth.domain.value_objects import RefreshToken


async def logout(provider: AuthProvider, refresh_token: str) -> None:
    await provider.logout(RefreshToken(refresh_token))
