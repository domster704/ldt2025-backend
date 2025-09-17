from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.interfaces import UserRepository
from app.modules.auth.domain.entities import User

from app.modules.core.adapters.common.db_models import AppUser, AppUserSettings

class SAUserRepository(UserRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def get_by_sub(self, sub: str) -> Optional[User]:
        async with self.session_factory() as s:  # type: AsyncSession
            row = await s.get(AppUser, sub)
            if not row:
                return None
            return User(id=row.id, username=row.username, email=row.email, is_active=row.is_active, roles=())

    async def upsert_from_claims(self, claims: dict) -> User:
        sub = claims["sub"]
        username = claims.get("preferred_username", sub)
        email = claims.get("email")
        enabled = claims.get("email_verified", True)

        async with self.session_factory() as s:
            user = await s.get(AppUser, sub)
            if user:
                user.username = username or user.username
                user.email = email if email is not None else user.email
                user.is_active = bool(enabled)
            else:
                user = AppUser(id=sub, username=username, email=email, is_active=bool(enabled))
                s.add(user)
                s.add(AppUserSettings(user_id=sub))

            await s.commit()

        return User(
            id=user.id, username=user.username, email=user.email,
            is_active=user.is_active, roles=(),
        )
