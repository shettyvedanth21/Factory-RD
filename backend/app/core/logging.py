import logging
import sys

import structlog
from structlog.types import Processor

from .config import settings


def configure_logging() -> None:
    """
    Configure structlog for the application.
    - JSON output in production
    - Console output in development
    - Adds timestamp, log_level, service to all entries
    """
    # Determine if we're in development
    is_development = settings.app_env == "development"
    
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
    root_logger.setLevel(settings.log_level.upper())
    
    # Silence noisy loggers
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with the given name.
    All logs will include service="api" by default.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("user_logged_in", user_id=123, factory_id=1)
    """
    logger = structlog.get_logger(name)
    return logger.bind(service="api")
