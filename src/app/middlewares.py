import uuid
import time

from starlette.types import ASGIApp, Scope, Receive, Send
from structlog.contextvars import bind_contextvars, unbind_contextvars


from urllib.parse import parse_qsl, urlencode

from app.logger import LogLike


class HTTPLogMiddleware:
    _REDACT_KEYS = {"authorization", "cookie", "set-cookie", "x-api-key", "api_key", "api-key", "token", "access_token", "refresh_token", "password"}

    @staticmethod
    def _redact_value(value: str) -> str:
        if not value:
            return value
        if len(value) <= 8:
            return "***"
        return value[:4] + "***" + value[-4:]

    @classmethod
    def _redact_query_string(cls, qs: str) -> str:
        try:
            pairs = parse_qsl(qs, keep_blank_values=True)
        except Exception:
            return qs
        redacted = []
        for k, v in pairs:
            if (k or "").lower() in cls._REDACT_KEYS:
                redacted.append((k, cls._redact_value(v)))
            else:
                redacted.append((k, v))
        return urlencode(redacted)

    def __init__(self, app: ASGIApp, logger: LogLike, dev: bool = False):
        self.app = app
        self._logger = logger
        self._dev = dev

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        raw_headers = scope.get("headers", [])
        headers = {k.decode().lower(): v.decode() for k, v in raw_headers}
        request_id = headers.get("x-request-id") or str(uuid.uuid4())

        method = scope.get("method")
        path = scope.get("path")
        raw_query = scope.get("query_string", b"")
        query_str = raw_query.decode() if isinstance(raw_query, (bytes, bytearray)) else str(raw_query or "")
        redacted_query = self._redact_query_string(query_str)

        xff = headers.get("x-forwarded-for")
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            client = scope.get("client")
            ip = client[0] if isinstance(client, (list, tuple)) and client else None

        user_agent = headers.get("user-agent")

        bind_contextvars(request_id=request_id)

        status = {"code": 500}

        async def send_wrapper(message: dict) -> None:
            if message.get("type") == "http.response.start":
                status["code"] = message.get("status")
                headers_list = message.get("headers")
                if headers_list is None:
                    headers_list = []
                    message["headers"] = headers_list
                has_xrid = any(hk.lower() == b"x-request-id" for hk, _ in headers_list)
                if not has_xrid:
                    headers_list.append((b"x-request-id", request_id.encode()))
            await send(message)

        self._logger.info(
            "http_request_start",
            id=request_id,
            method=method,
            path=path,
            query=redacted_query,
            client_ip=ip,
            ua=(user_agent or "")[:200],
            env=("dev" if self._dev else "prod"),
        )

        start_time = time.perf_counter()

        try:
            await self.app(scope, receive, send_wrapper)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            self._logger.info(
                "http_request_end",
                id=request_id,
                status=status["code"],
                duration_ms=duration_ms,
            )
        except Exception:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            code = status["code"] or 500
            self._logger.exception(
                "http_request_fail",
                id=request_id,
                status=code,
                duration_ms=duration_ms,
            )
            raise
        finally:
            unbind_contextvars('request_id')
