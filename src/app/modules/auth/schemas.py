from pydantic import BaseModel
from typing import Optional

class TokensOut(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None

class RefreshIn(BaseModel):
    refresh_token: str
