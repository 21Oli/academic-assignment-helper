"""
Structured JSON logging for the entire backend.

Import and use:
    from backend.logger import get_logger
    logger = get_logger(__name__)
    logger.info("user.registered", user_id=42, email="x@y.com")

In production the JSON output can be ingested by Datadog, CloudWatch,
Loki, or any log aggregator. In development it pretty-prints with colours.
"""
import logging
import os
import sys

import structlog


def _configure_logging() -> None:
    """Called once at import time to configure stdlib + structlog."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    is_dev = os.getenv("ENV", "development").lower() in ("development", "dev", "local")

    # --- stdlib root logger -------------------------------------------------
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )
    # Quieten noisy libraries
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # --- structlog processors -----------------------------------------------
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_dev:
        # Human-readable coloured output during local development
        renderer = structlog.dev.ConsoleRenderer()
    else:
        # Machine-readable JSON for production / Docker / CI
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, log_level, logging.INFO))


_configure_logging()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to the given module name."""
    return structlog.get_logger(name)
