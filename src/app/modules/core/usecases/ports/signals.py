from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.core.domain.ctg import CardiotocographyPoint


class SignalsPort(Protocol):
    def __init__(self, session: AsyncSession) -> None: ...

    def save(self, signal: CardiotocographyPoint) -> None: ...