from dataclasses import dataclass
from enum import Enum


class AuthStatus(Enum):
    ANONYMOUS = 'anonymous'
    AUTHENTICATED = 'authenticated'
    FORBIDDEN = 'forbidden'
    FAILED = 'failed'

class AuthErrorCode(Enum):
    INVALID_CREDENTIALS = "invalid_credentials"
    UNEXPECTED_ERROR = "unexpected_error"

@dataclass(frozen=True)
class AuthResult:
    status: AuthStatus
    app: ... | None
    error_code: AuthErrorCode | None
    message: str | None
    access_token: str | None
    refresh_token: str | None


def login(
        credentials: ...,
        auth_port: ...,
):
    app = auth_port.find_by_credentials(credentials)

    if not app:
        return AuthResult(
            status=AuthStatus.FORBIDDEN,
            app=None,
            error_code=AuthErrorCode.INVALID_CREDENTIALS,
            message="Invalid credentials",
            access_token=None,
            refresh_token=None,
        )

    access_token, refresh_token = auth_port.generate_tokens(app)

    return AuthResult(
        status=AuthStatus.AUTHENTICATED,
        app=app,
        error_code=None,
        message=None,
        access_token=access_token,
        refresh_token=refresh_token,
    )