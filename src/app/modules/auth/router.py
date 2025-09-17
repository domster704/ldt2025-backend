from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dishka.integrations.fastapi import FromDishka, inject

from app.modules.auth.domain.interfaces import AuthProvider, TokenVerifier, UserRepository
from app.modules.auth.schemas import TokensOut, RefreshIn
from app.modules.auth.usecases.login_with_code import login_with_code
from app.modules.auth.usecases.refresh_tokens import refresh_tokens
from app.modules.auth.usecases.logout import logout as uc_logout
from app.modules.auth.usecases.verify_access import verify_access
from app.modules.auth.usecases.get_current_user import get_current_user

router = APIRouter(prefix='/auth', tags=['Управление доступами'])
bearer = HTTPBearer(auto_error=False)

def _access_token(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return creds.credentials

@router.get("/login/callback")
@inject
async def login_callback(
    code: str,
    provider: FromDishka[AuthProvider],
    users: FromDishka[UserRepository],
) -> TokensOut:
    tokens = await login_with_code(provider, users, code)
    return TokensOut(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )

@router.post("/refresh")
@inject
async def refresh(
    inp: RefreshIn,
    provider: FromDishka[AuthProvider],
) -> TokensOut:
    tokens = await refresh_tokens(provider, inp.refresh_token)
    return TokensOut(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )

@router.post("/logout")
@inject
async def logout(
    inp: RefreshIn,
    provider: FromDishka[AuthProvider],
) -> dict[str, bool]:
    await uc_logout(provider, inp.refresh_token)
    return {"ok": True}

@router.get("/verify")
@inject
async def verify(
    token_verifier: FromDishka[TokenVerifier],
    access_token: str = Depends(_access_token),
):
    claims = await verify_access(token_verifier, access_token)
    return claims

@router.get("/me")
@inject
async def me(
    token_verifier: FromDishka[TokenVerifier],
    users: FromDishka[UserRepository],
    access_token: str = Depends(_access_token),
):
    if users is None:
        raise HTTPException(status_code=500, detail="User repository is not configured")
    user = await get_current_user(users, token_verifier, access_token)
    return user.__dict__ if user else {"user": None}
