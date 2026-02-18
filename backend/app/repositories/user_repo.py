from typing import Optional, List, Tuple
from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole


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


async def get_all(db: AsyncSession, factory_id: int) -> List[User]:
    """
    Get all users for a factory.
    
    Args:
        db: Database session
        factory_id: Factory ID for isolation
    
    Returns:
        List of User objects
    """
    result = await db.execute(
        select(User)
        .where(User.factory_id == factory_id)
        .order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    factory_id: int,
    email: str,
    hashed_password: str,
    role: UserRole,
    permissions: dict,
    whatsapp_number: Optional[str] = None
) -> User:
    """
    Create a new user.
    
    Args:
        db: Database session
        factory_id: Factory ID
        email: User email
        hashed_password: Hashed password
        role: User role
        permissions: Permissions dictionary
        whatsapp_number: Optional WhatsApp number
    
    Returns:
        Created User object
    """
    user = User(
        factory_id=factory_id,
        email=email,
        hashed_password=hashed_password,
        role=role,
        permissions=permissions,
        whatsapp_number=whatsapp_number,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_permissions(
    db: AsyncSession,
    factory_id: int,
    user_id: int,
    permissions: dict
) -> Optional[User]:
    """
    Update user permissions.
    
    Args:
        db: Database session
        factory_id: Factory ID for isolation
        user_id: User ID
        permissions: New permissions dictionary
    
    Returns:
        Updated User object or None if not found
    """
    result = await db.execute(
        select(User).where(
            User.factory_id == factory_id,
            User.id == user_id
        )
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.permissions = permissions
        await db.commit()
        await db.refresh(user)
    
    return user


async def deactivate(
    db: AsyncSession,
    factory_id: int,
    user_id: int
) -> Optional[User]:
    """
    Deactivate a user (soft delete).
    
    Args:
        db: Database session
        factory_id: Factory ID for isolation
        user_id: User ID
    
    Returns:
        Deactivated User object or None if not found
    """
    result = await db.execute(
        select(User).where(
            User.factory_id == factory_id,
            User.id == user_id
        )
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.is_active = False
        await db.commit()
        await db.refresh(user)
    
    return user


async def get_by_invite_token(db: AsyncSession, token: str) -> Optional[User]:
    """
    Get a user by invite token.
    
    Args:
        db: Database session
        token: Invite token
    
    Returns:
        User object or None if not found
    """
    result = await db.execute(
        select(User).where(User.invite_token == token)
    )
    return result.scalar_one_or_none()


async def set_password_and_activate(
    db: AsyncSession,
    user_id: int,
    hashed_password: str
) -> User:
    """
    Set password and activate user after invite acceptance.
    
    Args:
        db: Database session
        user_id: User ID
        hashed_password: Hashed password
    
    Returns:
        Updated User object
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one()
    
    user.hashed_password = hashed_password
    user.is_active = True
    user.invite_token = None
    user.invited_at = None
    
    await db.commit()
    await db.refresh(user)
    return user
