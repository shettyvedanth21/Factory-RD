"""
Telemetry service entry point.
Starts the MQTT subscriber and handles shutdown signals.
"""
import asyncio
import signal
import sys

from logging_config import configure_logging, get_logger
from subscriber import start


# Configure logging
configure_logging()
logger = get_logger(__name__)


def handle_shutdown(signum, frame):
    """Handle shutdown signals (SIGTERM, SIGINT)."""
    logger.info(
        "telemetry.shutdown_signal_received",
        signal=signum
    )
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


if __name__ == "__main__":
    logger.info("telemetry.starting")
    
    try:
        asyncio.run(start())
    except SystemExit:
        logger.info("telemetry.shutdown_complete")
    except Exception as e:
        logger.error(
            "telemetry.fatal_error",
            error=str(e),
            exc_info=True
        )
        sys.exit(1)
