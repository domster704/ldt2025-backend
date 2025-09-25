from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True, slots=True)
class App:
    id: UUID
    user_agent: str
    passphrase: str

@dataclass(frozen=True, slots=True)
class Tokens:
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None