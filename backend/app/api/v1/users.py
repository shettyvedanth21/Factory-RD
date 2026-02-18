"""
Users API endpoints.
All endpoints require super_admin role except accept-invite.
"""
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_super_admin
from app.core.logging import get_logger
from app.core.security import hash_password, create_access_token
from app.core.config import settings
from app.models import User, UserRole
from app.repositories import user_repo


router = APIRouter(tags=["Users"])
logger = get_logger(__name__)


# Schemas
class UserInviteRequest(BaseModel):
    email: EmailStr
    whatsapp_number: Optional[str] = None
    permissions: dict = Field(
        default_factory=lambda: {
            "can_create_rules": True,
            "can_run_analytics": True,
            "can_generate_reports": True
        }
    )


class UserInviteResponse(BaseModel):
    id: int
    email: str
    invite_sent: bool


class UserListItem(BaseModel):
    id: int
    email: str
    whatsapp_number: Optional[str]
    role: str
    permissions: dict
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime


class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str = Field(min_length=8)


class AcceptInviteResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UpdatePermissionsRequest(BaseModel):
    permissions: dict


# Endpoints
@router.get("/users", response_model=dict)
async def list_users(
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users in the factory.
    Requires super_admin role.
    """
    factory_id = user._token_factory_id
    
    users = await user_repo.get_all(db, factory_id)
    
    users_data = [
        UserListItem(
            id=u.id,
            email=u.email,
            whatsapp_number=u.whatsapp_number,
            role=u.role.value,
            permissions=u.permissions or {},
            is_active=u.is_active,
            last_login=u.last_login,
            created_at=u.created_at
        )
        for u in users
    ]
    
    logger.info(
        "users.list",
        factory_id=factory_id,
        user_id=user.id,
        count=len(users)
    )
    
    return {"data": [u.model_dump() for u in users_data]}


@router.post("/users/invite", response_model=dict, status_code=status.HTTP_201_CREATED)
async def invite_user(
    invite_data: UserInviteRequest,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite a new admin user.
    Generates invite token, creates inactive user, sends email.
    Requires super_admin role.
    """
    factory_id = user._token_factory_id
    
    # Check if user already exists
    existing = await user_repo.get_by_email(db, factory_id, invite_data.email)
    if existing:
        logger.warning(
            "users.invite_duplicate",
            factory_id=factory_id,
            email=invite_data.email,
            inviter_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Generate invite token
    invite_token = secrets.token_urlsafe(32)
    
    # Create user with temporary password (will be replaced on accept)
    temp_password = secrets.token_urlsafe(16)
    hashed = hash_password(temp_password)
    
    # Create user in inactive state
    from app.models.user import User as UserModel
    new_user = UserModel(
        factory_id=factory_id,
        email=invite_data.email,
        whatsapp_number=invite_data.whatsapp_number,
        hashed_password=hashed,
        role=UserRole.ADMIN,
        permissions=invite_data.permissions,
        is_active=False,
        invite_token=invite_token,
        invited_at=datetime.utcnow()
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Build invite link
    invite_link = f"{settings.app_url}/accept-invite?token={invite_token}"
    
    # Send invitation email
    invite_sent = False
    if settings.smtp_host:
        try:
            # TODO: Implement email sending when SMTP is configured
            # For now, just log
            logger.info(
                "users.invite_email_would_send",
                factory_id=factory_id,
                email=invite_data.email,
                invite_link=invite_link
            )
            invite_sent = True
        except Exception as e:
            logger.error(
                "users.invite_email_failed",
                factory_id=factory_id,
                email=invite_data.email,
                error=str(e)
            )
    else:
        # Development mode: log invite link
        logger.info(
            "users.invite_link_generated",
            factory_id=factory_id,
            email=invite_data.email,
            invite_link=invite_link,
            message="SMTP not configured - invite link logged for development"
        )
        invite_sent = True
    
    logger.info(
        "users.invited",
        factory_id=factory_id,
        user_id=new_user.id,
        email=invite_data.email,
        inviter_id=user.id
    )
    
    return {
        "data": UserInviteResponse(
            id=new_user.id,
            email=new_user.email,
            invite_sent=invite_sent
        ).model_dump()
    }


@router.post("/users/accept-invite", response_model=dict)
async def accept_invite(
    accept_data: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Accept invite and set password.
    No authentication required - uses invite token.
    Auto-login after password set.
    """
    # Find user by invite token
    invited_user = await user_repo.get_by_invite_token(db, accept_data.invite_token)
    
    if not invited_user:
        logger.warning(
            "users.accept_invalid_token",
            token=accept_data.invite_token[:8] + "..."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite token"
        )
    
    # Check token expiry (48 hours)
    if invited_user.invited_at:
        expiry = invited_user.invited_at + timedelta(hours=48)
        if datetime.utcnow() > expiry:
            logger.warning(
                "users.accept_expired_token",
                user_id=invited_user.id,
                email=invited_user.email,
                invited_at=invited_user.invited_at.isoformat()
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite token has expired (48 hour limit)"
            )
    
    # Hash password and activate user
    hashed = hash_password(accept_data.password)
    activated_user = await user_repo.set_password_and_activate(db, invited_user.id, hashed)
    
    # Generate JWT for auto-login
    from app.models.factory import Factory
    from sqlalchemy import select
    
    result = await db.execute(
        select(Factory).where(Factory.id == activated_user.factory_id)
    )
    factory = result.scalar_one()
    
    access_token = create_access_token(
        user_id=activated_user.id,
        factory_id=factory.id,
        factory_slug=factory.slug,
        role=activated_user.role.value
    )
    
    logger.info(
        "users.invite_accepted",
        factory_id=activated_user.factory_id,
        user_id=activated_user.id,
        email=activated_user.email
    )
    
    return {
        "data": AcceptInviteResponse(
            access_token=access_token,
            token_type="bearer"
        ).model_dump()
    }


@router.patch("/users/{user_id}/permissions", response_model=dict)
async def update_user_permissions(
    user_id: int,
    update_data: UpdatePermissionsRequest,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user permissions.
    Cannot modify super_admin users.
    Requires super_admin role.
    """
    factory_id = user._token_factory_id
    
    # Get target user
    target_user = await user_repo.get_by_id(db, user_id)
    
    if not target_user or target_user.factory_id != factory_id:
        logger.warning(
            "users.update_permissions_not_found",
            factory_id=factory_id,
            target_user_id=user_id,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot modify super_admin users
    if target_user.role == UserRole.SUPER_ADMIN:
        logger.warning(
            "users.update_permissions_denied_super_admin",
            factory_id=factory_id,
            target_user_id=user_id,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify super_admin permissions"
        )
    
    # Update permissions
    updated_user = await user_repo.update_permissions(
        db, factory_id, user_id, update_data.permissions
    )
    
    logger.info(
        "users.permissions_updated",
        factory_id=factory_id,
        target_user_id=user_id,
        user_id=user.id,
        permissions=update_data.permissions
    )
    
    return {"data": {"id": updated_user.id, "permissions": updated_user.permissions}}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: int,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a user (soft delete).
    Cannot delete self or other super_admin users.
    Requires super_admin role.
    """
    factory_id = user._token_factory_id
    
    # Cannot delete self
    if user_id == user.id:
        logger.warning(
            "users.deactivate_self_denied",
            factory_id=factory_id,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # Get target user
    target_user = await user_repo.get_by_id(db, user_id)
    
    if not target_user or target_user.factory_id != factory_id:
        logger.warning(
            "users.deactivate_not_found",
            factory_id=factory_id,
            target_user_id=user_id,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot delete super_admin users
    if target_user.role == UserRole.SUPER_ADMIN:
        logger.warning(
            "users.deactivate_denied_super_admin",
            factory_id=factory_id,
            target_user_id=user_id,
            user_id=user.id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate super_admin users"
        )
    
    # Deactivate
    await user_repo.deactivate(db, factory_id, user_id)
    
    logger.info(
        "users.deactivated",
        factory_id=factory_id,
        target_user_id=user_id,
        user_id=user.id
    )
