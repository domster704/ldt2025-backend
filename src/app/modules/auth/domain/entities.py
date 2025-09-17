from dataclasses import dataclass
from typing import Optional, AnyStr


@dataclass(frozen=True, slots=True)
class User:
    id: AnyStr
    username: AnyStr
    email: str | None = None
    is_active: bool = True
    roles: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class Tokens:
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None