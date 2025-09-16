from __future__ import annotations

import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import bcrypt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status, Body,
)
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from api.deps import UserRepositoryDepends
from db.models import User
from settings import settings

SECRET_KEY = settings.jwt.secret.get_secret_value()
ALGORITHM = settings.jwt.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt.ttl_minutes

security_router = APIRouter(tags=["auth"])


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def _get_current_user(
        request: Request,
        user_repository=UserRepositoryDepends
) -> User:
    """Определяет пользователя по JWT.

    1. Сначала пробуем взять расшифрованный payload,
       который положил AuthMiddleware.
    2. Если payload нет — читаем заголовок ``Authorization``
       и декодируем токен вручную.
    """
    login: str | None = getattr(request.state, "user", None)
    if login is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    user = await user_repository.get(login)

    response = Response()
    request.state._custom_response = response
    return user


def _get_token(username: str):
    return _create_access_token(
        {"sub": username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


@security_router.post("/login")
async def login(
        form: Annotated[OAuth2PasswordRequestForm, Depends()],
        user_repository=UserRepositoryDepends
):
    try:
        user = await user_repository.get(form.username)
        if not bcrypt.checkpw(form.password.encode(), user.password.encode()):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad credentials")
    except Exception as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad credentials")

    return {
        "user": {
            "id": user.id,
            "login": user.username,
        },
        "JWT": _get_token(user.username)
    }


@security_router.post("/")
async def telegram_login(
        init_data: str = Body(embed=True),
        user_repository=UserRepositoryDepends
):
    try:
        payload = verify_telegram_data(init_data, settings.bot.token)
    except ValueError:
        raise HTTPException(401, "Invalid Telegram initData")

    tg_user = payload["user"]
    tg_id = str(tg_user["id"])

    user = await user_repository.get(tg_id)

    jwt_token = _create_access_token({"sub": tg_id})
    return {"JWT": jwt_token, "user": user.model_dump()}


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware, проводящий JWT-аутентификацию для каждого запроса.

    * Проверяет наличие и корректность заголовка ``Authorization: Bearer …``.
    * Декодирует токен и сохраняет payload в ``request.state.jwt_payload``.
    * Пропускает «белый список» эндпоинтов (документация, логин и т. д.).
    """

    # Эндпоинты, которые не требуют токена
    _EXEMPT: set[str] = {
        "/import",
        "/login",
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        "/health",
    }

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основной обработчик middleware.

        Args:
            request: входящий запрос.
            call_next: функция передачи управления следующему медлу.

        Returns:
            HTTP-ответ.

        Raises:
            HTTPException: 401, если токен отсутствует или некорректен.
        """
        if request.url.path in self._EXEMPT:
            return await call_next(request)

        header: str | None = request.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing bearer token"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        token: str = header.removeprefix("Bearer ").strip()

        if token in settings.security.apikeys:
            return await call_next(request)

        try:
            payload: dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            return JSONResponse(
                {"detail": "Invalid token"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        request.state.user = payload['sub']
        return await call_next(request)


def verify_telegram_data(init_data: str, bot_token: str) -> bool:
    try:
        data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

        received_hash = data.pop('hash')
        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        return calculated_hash == received_hash.lower()
    except Exception as e:
        print("verify error:", e)
        return False


if __name__ == "__main__":
    a = "query_id=AAHhIB8tAAAAAOEgHy1ln0ig&user=%7B%22id%22%3A757014753%2C%22first_name%22%3A%22%D0%93%D1%80%D0%B8%D0%B3%D0%BE%D1%80%D0%B8%D0%B9%22%2C%22last_name%22%3A%22%D0%98%D1%81%D1%83%D0%BF%D0%BE%D0%B2%22%2C%22username%22%3A%22domster704%22%2C%22language_code%22%3A%22ru%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FAY3NAoFhtI4bvTxzWkG2Ue8oTy395tJ1RFLHnl0dUeE.svg%22%7D&auth_date=1758031217&signature=usm7H4r1dRRJox4EF6R-klJikkpvIVkUE4vDvgaDhk83mpq3BN4Hq2GwM4wDsB5D863brJIFWmCyx5bjlmb0AQ&hash=f9ea6827b6c471b1ab57fc94033d729c3e96201e7d2d7e475919bfbbd547c638"
    print(verify_telegram_data(a, settings.bot.token.get_secret_value()))
