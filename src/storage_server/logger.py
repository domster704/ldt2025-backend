import logging
from typing import Protocol, Any

import structlog


class LogLike(Protocol):
    def info(self, event: str, /, **kw: Any) -> Any: ...
    def error(self, event: str, /, **kw: Any) -> Any: ...
    def debug(self, event: str, /, **kw: Any) -> Any: ...
    def warning(self, event: str, /, **kw: Any) -> Any: ...
    def exception(self, event: str, /, **kw: Any) -> Any: ...

def setup_logger(is_dev: bool) -> None:
    try:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.add_log_level,
        ]
        if is_dev:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        else:
            processors.append(structlog.processors.JSONRenderer())

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.DEBUG if is_dev else logging.INFO
            )
        )
    except Exception:
        pass
