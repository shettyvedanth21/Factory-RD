"""
Integration tests for the telemetry pipeline.
These tests verify the end-to-end flow from MQTT message to database/InfluxDB.
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json

import sys
from pathlib import Path

# Add telemetry module to path
telemetry_path = Path(__file__).parent.parent.parent.parent / "telemetry"
sys.path.insert(0, str(telemetry_path))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Factory, Device, DeviceParameter

# Import telemetry modules
from handlers.ingestion import process_telemetry
from schemas import TelemetryPayload


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create a test database engine."""
    from app.models import Base
    
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Create a test database session."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.rollback()  # Rollback any changes after test


@pytest.fixture
async def test_factory(db_session):
    """Create a test factory."""
    factory = Factory(
        id=1,
        name="Test Factory",
        slug="test",
        timezone="UTC"
    )
    db_session.add(factory)
    await db_session.commit()
    await db_session.refresh(factory)
    return factory


@pytest.fixture
async def test_device(db_session, test_factory):
    """Create a test device."""
    device = Device(
        id=1,
        factory_id=test_factory.id,
        device_key="TEST01",
        name="Test Device",
        is_active=True
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis


@pytest.fixture
def mock_influx_write_api():
    """Create a mock InfluxDB write API."""
    write_api = AsyncMock()
    write_api.write = AsyncMock()
    return write_api


@pytest.mark.asyncio
class TestTelemetryPipeline:
    """Integration tests for telemetry pipeline."""
    
    async def test_valid_payload_writes_to_influxdb(
        self,
        db_session,
        test_factory,
        test_device,
        mock_redis,
        mock_influx_write_api
    ):
        """Test that valid payload successfully writes to InfluxDB."""
        # Prepare test data
        topic = "factories/test/devices/TEST01/telemetry"
        payload_data = {
            "timestamp": "2024-01-15T10:00:00Z",
            "metrics": {
                "temperature": 45.5,
                "pressure": 101.3,
                "rpm": 1500
            }
        }
        payload = json.dumps(payload_data).encode("utf-8")
        
        # Mock Redis to return factory (to skip cache miss)
        mock_redis.get = AsyncMock(side_effect=[
            json.dumps({"id": 1, "name": "Test Factory", "slug": "test", "timezone": "UTC"}),  # factory
            json.dumps({"id": 1, "factory_id": 1, "device_key": "TEST01", "name": "Test Device", "is_active": True})  # device
        ])
        
        # Process telemetry
        await process_telemetry(
            topic=topic,
            payload=payload,
            db=db_session,
            redis=mock_redis,
            influx_write_api=mock_influx_write_api
        )
        
        # Verify InfluxDB write was called
        assert mock_influx_write_api.write.called
        
        # Verify device_parameters were created
        result = await db_session.execute(
            select(DeviceParameter).where(DeviceParameter.device_id == test_device.id)
        )
        parameters = result.scalars().all()
        
        assert len(parameters) == 3
        param_keys = {p.parameter_key for p in parameters}
        assert param_keys == {"temperature", "pressure", "rpm"}
    
    async def test_malformed_payload_does_not_crash(
        self,
        db_session,
        test_factory,
        test_device,
        mock_redis,
        mock_influx_write_api
    ):
        """Test that malformed payload is logged without crashing."""
        topic = "factories/test/devices/TEST01/telemetry"
        payload = b"invalid json{{"
        
        # Mock Redis to return factory
        mock_redis.get = AsyncMock(return_value=None)
        
        # This should not raise an exception
        await process_telemetry(
            topic=topic,
            payload=payload,
            db=db_session,
            redis=mock_redis,
            influx_write_api=mock_influx_write_api
        )
        
        # Verify InfluxDB write was NOT called
        assert not mock_influx_write_api.write.called
    
    async def test_unknown_factory_skips_processing(
        self,
        db_session,
        mock_redis,
        mock_influx_write_api
    ):
        """Test that unknown factory slug skips processing."""
        topic = "factories/unknown/devices/TEST01/telemetry"
        payload_data = {
            "metrics": {
                "temperature": 45.5
            }
        }
        payload = json.dumps(payload_data).encode("utf-8")
        
        # Mock Redis to return None (factory not found)
        mock_redis.get = AsyncMock(return_value=None)
        
        # Process telemetry
        await process_telemetry(
            topic=topic,
            payload=payload,
            db=db_session,
            redis=mock_redis,
            influx_write_api=mock_influx_write_api
        )
        
        # Verify InfluxDB write was NOT called
        assert not mock_influx_write_api.write.called
    
    async def test_new_parameter_key_auto_discovered(
        self,
        db_session,
        test_factory,
        test_device,
        mock_redis,
        mock_influx_write_api
    ):
        """Test that new parameter keys are auto-discovered."""
        # First, create one existing parameter
        existing_param = DeviceParameter(
            factory_id=test_factory.id,
            device_id=test_device.id,
            parameter_key="existing_param",
            data_type="float",
            is_kpi_selected=True
        )
        db_session.add(existing_param)
        await db_session.commit()
        
        # Prepare test data with new parameter
        topic = "factories/test/devices/TEST01/telemetry"
        payload_data = {
            "metrics": {
                "existing_param": 100.0,
                "new_param": 200.0
            }
        }
        payload = json.dumps(payload_data).encode("utf-8")
        
        # Mock Redis to return factory and device
        mock_redis.get = AsyncMock(side_effect=[
            json.dumps({"id": 1, "name": "Test Factory", "slug": "test", "timezone": "UTC"}),
            json.dumps({"id": 1, "factory_id": 1, "device_key": "TEST01", "name": "Test Device", "is_active": True})
        ])
        
        # Process telemetry
        await process_telemetry(
            topic=topic,
            payload=payload,
            db=db_session,
            redis=mock_redis,
            influx_write_api=mock_influx_write_api
        )
        
        # Verify both parameters exist
        result = await db_session.execute(
            select(DeviceParameter).where(DeviceParameter.device_id == test_device.id)
        )
        parameters = result.scalars().all()
        
        assert len(parameters) == 2
        param_keys = {p.parameter_key for p in parameters}
        assert param_keys == {"existing_param", "new_param"}
    
    async def test_invalid_topic_format_skips_processing(
        self,
        db_session,
        mock_redis,
        mock_influx_write_api
    ):
        """Test that invalid topic format is logged without crashing."""
        topic = "invalid/topic/format"
        payload_data = {"metrics": {"temperature": 45.5}}
        payload = json.dumps(payload_data).encode("utf-8")
        
        # This should not raise an exception
        await process_telemetry(
            topic=topic,
            payload=payload,
            db=db_session,
            redis=mock_redis,
            influx_write_api=mock_influx_write_api
        )
        
        # Verify InfluxDB write was NOT called
        assert not mock_influx_write_api.write.called
    
    async def test_empty_metrics_skips_processing(
        self,
        db_session,
        test_factory,
        mock_redis,
        mock_influx_write_api
    ):
        """Test that empty metrics dict is rejected."""
        topic = "factories/test/devices/TEST01/telemetry"
        payload_data = {"metrics": {}}
        payload = json.dumps(payload_data).encode("utf-8")
        
        # This should not raise an exception
        await process_telemetry(
            topic=topic,
            payload=payload,
            db=db_session,
            redis=mock_redis,
            influx_write_api=mock_influx_write_api
        )
        
        # Verify InfluxDB write was NOT called
        assert not mock_influx_write_api.write.called
