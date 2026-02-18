import logging
import sys
import os

import structlog
from structlog.types import Processor


def configure_logging() -> None:
    """
    Configure structlog for the telemetry service.
    - JSON output in production
    - Console output in development
    - Adds timestamp, log_level, service to all entries
    """
    # Determine if we're in development
    app_env = os.getenv("APP_ENV", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    is_development = app_env == "development"
    
    # Shared processors for both structlog and stdlib
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure stdlib logging
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer() if is_development else structlog.processors.JSONRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())
    
    # Silence noisy loggers
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with the given name.
    All logs will include service="telemetry" by default.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("device_registered", device_id=123, factory_id=1)
    """
    logger = structlog.get_logger(name)
    return logger.bind(service="telemetry")
