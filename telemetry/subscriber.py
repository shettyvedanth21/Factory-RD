"""
MQTT subscriber for telemetry ingestion.
Subscribes to factories/+/devices/+/telemetry and processes messages.
"""
import asyncio

import aiomqtt
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

from config import settings
from database import get_db_session
from redis_client import get_redis_client
from handlers.ingestion import process_telemetry
from logging_config import get_logger


logger = get_logger(__name__)


async def start():
    """
    Start the MQTT subscriber with automatic reconnection.
    
    This function implements the main event loop for the telemetry service.
    It handles:
    - MQTT connection with credentials
    - Wildcard subscription to all factory/device telemetry topics
    - Automatic reconnection with exponential backoff
    - Message processing through the ingestion pipeline
    
    CRITICAL: This loop must never crash. All exceptions are caught and logged.
    """
    retry_delay = 1  # Start with 1 second delay
    
    while True:
        try:
            # Create MQTT client
            async with aiomqtt.Client(
                hostname=settings.mqtt_broker_host,
                port=settings.mqtt_broker_port,
                username=settings.mqtt_username if settings.mqtt_username else None,
                password=settings.mqtt_password if settings.mqtt_password else None,
            ) as client:
                # Connection successful - reset retry delay
                retry_delay = 1
                
                logger.info(
                    "mqtt.connected",
                    host=settings.mqtt_broker_host,
                    port=settings.mqtt_broker_port
                )
                
                # Subscribe to all factory/device telemetry topics
                await client.subscribe("factories/+/devices/+/telemetry")
                logger.info(
                    "mqtt.subscribed",
                    topic="factories/+/devices/+/telemetry"
                )
                
                # Create InfluxDB client
                influx_client = InfluxDBClientAsync(
                    url=settings.influxdb_url,
                    token=settings.influxdb_token,
                    org=settings.influxdb_org
                )
                influx_write_api = influx_client.write_api()
                
                try:
                    # Process messages
                    async for message in client.messages:
                        # Get fresh DB and Redis connections for each message
                        async with get_db_session() as db, get_redis_client() as redis:
                            await process_telemetry(
                                topic=str(message.topic),
                                payload=message.payload,
                                db=db,
                                redis=redis,
                                influx_write_api=influx_write_api,
                            )
                finally:
                    # Clean up InfluxDB connection
                    await influx_write_api.close()
                    await influx_client.close()
        
        except aiomqtt.MqttError as e:
            # MQTT connection error - retry with exponential backoff
            logger.error(
                "mqtt.disconnected",
                error=str(e),
                retry_in=retry_delay
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Max 60 seconds
        
        except Exception as e:
            # Unexpected error - log and retry
            logger.error(
                "mqtt.unexpected_error",
                error=str(e),
                exc_info=True,
                retry_in=retry_delay
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Max 60 seconds
