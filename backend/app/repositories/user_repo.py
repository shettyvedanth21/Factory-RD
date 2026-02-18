from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Get a user by ID.
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        User object or None if not found
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, factory_id: int, email: str) -> Optional[User]:
    """
    Get a user by email within a factory.
    
    Args:
        db: Database session
        factory_id: Factory ID for isolation
        email: User email
    
    Returns:
        User object or None if not found
    """
    result = await db.execute(
        select(User).where(
            User.factory_id == factory_id,
            User.email == email
        )
    )
    return result.scalar_one_or_none()
