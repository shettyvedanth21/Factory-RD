from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.repositories import user_repo


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
    
    Returns:
        User object with _token_factory_id attached
    
    Raises:
        HTTPException: If token is invalid or user not found/inactive
    """
    # Decode token
    payload = decode_access_token(token)
    
    # Get user from database
    user_id = int(payload["sub"])
    user = await user_repo.get_by_id(db, user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Attach factory_id from token for downstream use
    user._token_factory_id = payload["factory_id"]
    user._token_factory_slug = payload["factory_slug"]
    user._token_role = payload["role"]
    
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """
    Require that the current user is a super admin.
    
    Args:
        user: Current authenticated user
    
    Returns:
        User object if super admin
    
    Raises:
        HTTPException: If user is not a super admin
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required"
        )
    return user


def require_permission(permission_key: str):
    """
    Create a dependency that requires a specific permission.
    Super admins bypass permission checks.
    
    Args:
        permission_key: Permission key to check (e.g., "can_create_rules")
    
    Returns:
        Dependency function that validates the permission
    """
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        # Super admins have all permissions
        if user.role.value == "super_admin":
            return user
        
        # Check if user has the required permission
        if not user.permissions or not user.permissions.get(permission_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_key}' required"
            )
        
        return user
    
    return permission_checker
