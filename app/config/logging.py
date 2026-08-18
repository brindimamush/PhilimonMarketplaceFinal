import json
import logging
from contextvars import ContextVar
from typing import Any

# Context variables for request tracing across async tasks
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
telegram_id_ctx: ContextVar[int | None] = ContextVar("telegram_id", default=None)


class JSONFormatter(logging.Formatter):
    """Structured JSON logging formatter for production log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "context": {
                "request_id": request_id_ctx.get(),
                "telegram_id": telegram_id_ctx.get(),
                "operation": getattr(record, "operation", None),
                "entity_id": getattr(record, "entity_id", None),
                "status": getattr(record, "status", None),
                "error": getattr(record, "error", None),
            },
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps({k: v for k, v in log_obj.items() if v is not None})


def setup_logging(log_level: str = "INFO") -> None:
    """Configures system-wide structured logging."""
    logger = logging.getLogger()
    logger.setLevel(log_level)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    logger.handlers.clear()
    logger.addHandler(handler)
