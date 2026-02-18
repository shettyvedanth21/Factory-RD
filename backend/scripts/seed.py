"""
Seed script to populate initial data for development.
Run: python scripts/seed.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
import bcrypt

from app.core.database import AsyncSessionLocal
from app.models import Factory, User, Device, UserRole


async def seed_data():
    """Seed initial data for development."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if factory already exists
            result = await session.execute(select(Factory).where(Factory.slug == "vpc"))
            existing_factory = result.scalar_one_or_none()
            
            if existing_factory:
                print("✓ Data already seeded. Skipping...")
                return
            
            # Create Factory
            factory = Factory(
                name="VPC Factory",
                slug="vpc",
                timezone="Asia/Kolkata"
            )
            session.add(factory)
            await session.flush()  # Get factory.id
            
            print(f"✓ Created factory: {factory.name} (ID: {factory.id})")
            
            # Create SuperAdmin User
            password = "Admin@123"
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            admin_user = User(
                factory_id=factory.id,
                email="admin@vpc.com",
                hashed_password=hashed_password,
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                permissions={"can_create_rules": True, "can_run_analytics": True}
            )
            session.add(admin_user)
            await session.flush()
            
            print(f"✓ Created admin user: {admin_user.email} (ID: {admin_user.id})")
            print(f"  Password: Admin@123")
            
            # Create Device 1
            device1 = Device(
                factory_id=factory.id,
                device_key="M01",
                name="Compressor 1",
                manufacturer="Siemens",
                region="Zone A",
                is_active=True
            )
            session.add(device1)
            
            # Create Device 2
            device2 = Device(
                factory_id=factory.id,
                device_key="M02",
                name="Pump 1",
                manufacturer="ABB",
                region="Zone B",
                is_active=True
            )
            session.add(device2)
            await session.flush()
            
            print(f"✓ Created device: {device1.name} (ID: {device1.id}, Key: {device1.device_key})")
            print(f"✓ Created device: {device2.name} (ID: {device2.id}, Key: {device2.device_key})")
            
            # Commit all changes
            await session.commit()
            
            print("\n✅ Seed data inserted successfully!")
            print(f"\nFactory: {factory.name}")
            print(f"Admin: {admin_user.email} / Admin@123")
            print(f"Devices: {device1.device_key}, {device2.device_key}")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error seeding data: {e}")
            raise


if __name__ == "__main__":
    # Set DATABASE_URL if not already set
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "mysql+aiomysql://factoryops:factoryops_dev@localhost:3306/factoryops"
    
    asyncio.run(seed_data())
