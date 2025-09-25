from asyncio import Protocol
from dataclasses import dataclass
from uuid import UUID

from app.modules.auth.domain.entities import App


@dataclass(frozen=True)
class Credentials:
    id: UUID
    password: str
    roles: str

class AuthPort(Protocol):

    async def find_by_credentials(self, credentials: Credentials) -> App: