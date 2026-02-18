from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.core.config import settings
from app.models import Factory, User
from app.repositories import user_repo
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse, FactoryResponse


router = APIRouter(tags=["Authentication"])
logger = get_logger(__name__)


@router.get("/factories", response_model=dict)
async def get_factories(db: AsyncSession = Depends(get_db)):
    """
    Get all factories (public endpoint).
    Used for factory selector on login page.
    
    Returns:
        List of factories with id, name, and slug
    """
    result = await db.execute(select(Factory))
    factories = result.scalars().all()
    
    return {
        "data": [
            FactoryResponse(
                id=f.id,
                name=f.name,
                slug=f.slug
            ).model_dump()
            for f in factories
        ]
    }


@router.post("/auth/login", response_model=dict)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user within a factory context.
    
    Args:
        credentials: Login credentials (factory_id, email, password)
        db: Database session
    
    Returns:
        JWT token and user information
    
    Raises:
        HTTPException: If credentials are invalid
    """
    # Verify factory exists
    factory_result = await db.execute(
        select(Factory).where(Factory.id == credentials.factory_id)
    )
    factory = factory_result.scalar_one_or_none()
    
    if not factory:
        logger.warning(
            "login_failed_invalid_factory",
            factory_id=credentials.factory_id,
            email=credentials.email
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Get user by email within factory
    user = await user_repo.get_by_email(db, credentials.factory_id, credentials.email)
    
    if not user:
        logger.warning(
            "login_failed_user_not_found",
            factory_id=credentials.factory_id,
            email=credentials.email
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        logger.warning(
            "login_failed_invalid_password",
            factory_id=credentials.factory_id,
            email=credentials.email,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(
            "login_failed_inactive_user",
            factory_id=credentials.factory_id,
            email=credentials.email,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    # Create JWT token
    access_token = create_access_token(
        user_id=user.id,
        factory_id=factory.id,
        factory_slug=factory.slug,
        role=user.role.value
    )
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    await db.commit()
    
    logger.info(
        "user_logged_in",
        user_id=user.id,
        factory_id=factory.id,
        email=user.email,
        role=user.role.value
    )
    
    return {
        "data": LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expiry_hours * 3600,
            user=UserResponse(
                id=user.id,
                email=user.email,
                role=user.role.value,
                permissions=user.permissions or {}
            )
        ).model_dump()
    }


@router.post("/auth/refresh", response_model=dict)
async def refresh_token(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh JWT access token.
    Uses existing token to generate a new one with same factory context.
    
    Args:
        user: Current authenticated user
        db: Database session
    
    Returns:
        New JWT token and user information
    """
    # Get factory
    factory_result = await db.execute(
        select(Factory).where(Factory.id == user.factory_id)
    )
    factory = factory_result.scalar_one_or_none()
    
    if not factory:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Factory not found"
        )
    
    # Create new JWT token
    access_token = create_access_token(
        user_id=user.id,
        factory_id=factory.id,
        factory_slug=factory.slug,
        role=user.role.value
    )
    
    logger.info(
        "token_refreshed",
        user_id=user.id,
        factory_id=factory.id,
        email=user.email
    )
    
    return {
        "data": LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expiry_hours * 3600,
            user=UserResponse(
                id=user.id,
                email=user.email,
                role=user.role.value,
                permissions=user.permissions or {}
            )
        ).model_dump()
    }
