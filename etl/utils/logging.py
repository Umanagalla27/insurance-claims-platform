"""
etl/utils/logging.py
====================
Structured logging configuration using structlog.
Standardizes log output across all pipeline components for easy ingestion by
log aggregators (CloudWatch, Datadog, ELK).
"""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> structlog.BoundLogger:
    """Configures structured logging with ISO timestamps and contextual key-values."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            # Pretty console printing for dev; in cloud production, replace with JSONRenderer
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


logger = configure_logging()
