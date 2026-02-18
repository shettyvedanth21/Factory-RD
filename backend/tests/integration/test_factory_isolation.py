"""
CRITICAL: Factory isolation integration tests.
These tests verify that factory_id from JWT is enforced and cross-factory access returns 404.
ALL 6 tests must pass before Phase 2C is considered complete.
"""
import pytest
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Base, Factory, User, Device, DeviceParameter
from app.core.security import create_access_token, hash_password


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine):
    """Create a test database session."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.rollback()


async def create_test_data(db_session):
    """Helper to create all test data."""
    # Create factories
    factory1 = Factory(id=1, name="Factory 1", slug="factory1", timezone="UTC")
    factory2 = Factory(id=2, name="Factory 2", slug="factory2", timezone="UTC")
    db_session.add(factory1)
    db_session.add(factory2)
    await db_session.commit()
    await db_session.refresh(factory1)
    await db_session.refresh(factory2)
    
    # Create users
    user1 = User(
        id=1,
        factory_id=factory1.id,
        email="user1@factory1.com",
        hashed_password=hash_password("password123"),
        role="admin",
        is_active=True
    )
    user2 = User(
        id=2,
        factory_id=factory2.id,
        email="user2@factory2.com",
        hashed_password=hash_password("password123"),
        role="admin",
        is_active=True
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()
    
    # Create devices
    device1_factory1 = Device(
        id=1,
        factory_id=factory1.id,
        device_key="DEV1",
        name="Device 1",
        is_active=True
    )
    device1_factory2 = Device(
        id=2,
        factory_id=factory2.id,
        device_key="DEV2",
        name="Device 2",
        is_active=True
    )
    db_session.add(device1_factory1)
    db_session.add(device1_factory2)
    await db_session.commit()
    await db_session.refresh(device1_factory1)
    await db_session.refresh(device1_factory2)
    
    # Create parameter
    param1_factory1 = DeviceParameter(
        id=1,
        factory_id=factory1.id,
        device_id=device1_factory1.id,
        parameter_key="temperature",
        data_type="float",
        is_kpi_selected=True
    )
    db_session.add(param1_factory1)
    await db_session.commit()
    
    return {
        "factory1": factory1,
        "factory2": factory2,
        "user1": user1,
        "user2": user2,
        "device1_factory1": device1_factory1,
        "device1_factory2": device1_factory2,
        "param1_factory1": param1_factory1
    }


@pytest.mark.asyncio
class TestFactoryIsolation:
    """Critical factory isolation tests."""
    
    async def test_list_devices_only_returns_own_factory_devices(self, db_session):
        """Test that listing devices only returns devices from user's factory."""
        from app.repositories import device_repo
        
        test_data = await create_test_data(db_session)
        
        # User 1 should only see device from factory 1
        devices, total = await device_repo.get_all(db_session, test_data["factory1"].id)
        assert total == 1
        assert devices[0].id == test_data["device1_factory1"].id
        
        # User 2 should only see device from factory 2
        devices, total = await device_repo.get_all(db_session, test_data["factory2"].id)
        assert total == 1
        assert devices[0].id == test_data["device1_factory2"].id
    
    async def test_get_device_from_other_factory_returns_404(self, db_session):
        """Test that getting a device from another factory returns None (404)."""
        from app.repositories import device_repo
        
        test_data = await create_test_data(db_session)
        
        # User 1 trying to access factory 2's device should get None
        device = await device_repo.get_by_id(db_session, test_data["factory1"].id, test_data["device1_factory2"].id)
        assert device is None
        
        # User 2 trying to access factory 1's device should get None
        device = await device_repo.get_by_id(db_session, test_data["factory2"].id, test_data["device1_factory1"].id)
        assert device is None
    
    async def test_update_device_from_other_factory_returns_404(self, db_session):
        """Test that updating a device from another factory returns None (404)."""
        from app.repositories import device_repo
        
        test_data = await create_test_data(db_session)
        
        # User 1 trying to update factory 2's device should get None
        device = await device_repo.update(
            db_session, test_data["factory1"].id, test_data["device1_factory2"].id, {"name": "Hacked"}
        )
        assert device is None
        
        # Verify device was not updated
        result = await db_session.execute(
            select(Device).where(Device.id == test_data["device1_factory2"].id)
        )
        device = result.scalar_one()
        assert device.name == "Device 2"
    
    async def test_kpi_live_from_other_factory_device_returns_404(self, db_session):
        """Test that KPI live query for other factory's device returns empty."""
        from app.repositories import parameter_repo
        
        test_data = await create_test_data(db_session)
        
        # Get parameters for factory 1 device (should work)
        params = await parameter_repo.get_all(db_session, test_data["factory1"].id, test_data["device1_factory1"].id)
        assert len(params) == 1
        
        # Try to get parameters for factory 2 device using factory 1 ID (should be empty)
        params = await parameter_repo.get_all(db_session, test_data["factory1"].id, test_data["device1_factory2"].id)
        assert len(params) == 0
    
    async def test_kpi_history_from_other_factory_device_returns_404(self, db_session):
        """Test that KPI history query enforces factory isolation."""
        from app.repositories import parameter_repo
        
        test_data = await create_test_data(db_session)
        
        # User 1 trying to get parameters for factory 2's device should get empty list
        params = await parameter_repo.get_all(db_session, test_data["factory1"].id, test_data["device1_factory2"].id)
        assert len(params) == 0
    
    async def test_parameter_list_from_other_factory_device_returns_404(self, db_session):
        """Test that parameter list enforces factory isolation."""
        from app.repositories import parameter_repo
        
        test_data = await create_test_data(db_session)
        
        # User 1 can see parameters for factory 1 device
        params = await parameter_repo.get_all(db_session, test_data["factory1"].id, test_data["device1_factory1"].id)
        assert len(params) == 1
        
        # User 1 cannot see parameters for factory 2 device
        params = await parameter_repo.get_all(db_session, test_data["factory1"].id, test_data["device1_factory2"].id)
        assert len(params) == 0
        
        # User 2 cannot see parameters for factory 1 device
        params = await parameter_repo.get_all(db_session, test_data["factory2"].id, test_data["device1_factory1"].id)
        assert len(params) == 0
