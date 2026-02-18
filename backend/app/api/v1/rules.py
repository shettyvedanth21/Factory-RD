from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.models import User
from app.schemas.rule import RuleCreate, RuleUpdate, RuleResponse
from app.repositories import rule_repo


router = APIRouter(tags=["Rules"])
logger = get_logger(__name__)


@router.get("/rules", response_model=dict)
async def list_rules(
    device_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    scope: Optional[Literal["device", "global"]] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all rules for the current factory.
    
    Can filter by device_id (returns global + device-specific rules),
    is_active, and scope.
    """
    factory_id = user._token_factory_id
    
    rules, total = await rule_repo.get_all(
        db, factory_id, device_id, is_active, scope, page, per_page
    )
    
    # Build response with device_ids
    rules_data = []
    for rule in rules:
        rule_dict = RuleResponse.model_validate(rule).model_dump()
        # Get device IDs from relationship
        rule_dict["device_ids"] = [d.id for d in rule.devices]
        rules_data.append(rule_dict)
    
    return {
        "data": rules_data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.post("/rules", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_data: RuleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new rule.
    
    For device-scoped rules, device_ids must be provided.
    For global rules, device_ids are ignored.
    """
    factory_id = user._token_factory_id
    
    # Validate device scope
    if rule_data.scope == "device" and not rule_data.device_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="device_ids required for device-scoped rules"
        )
    
    # Create rule
    rule = await rule_repo.create(
        db, factory_id, user.id,
        rule_data.model_dump()
    )
    
    logger.info(
        "rule.created",
        factory_id=factory_id,
        rule_id=rule.id,
        scope=rule.scope,
        user_id=user.id
    )
    
    # Build response
    rule_dict = RuleResponse.model_validate(rule).model_dump()
    rule_dict["device_ids"] = [d.id for d in rule.devices]
    
    return {"data": rule_dict}


@router.get("/rules/{rule_id}", response_model=dict)
async def get_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get rule details.
    
    Returns 404 if rule not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    rule = await rule_repo.get_by_id(db, factory_id, rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    # Build response
    rule_dict = RuleResponse.model_validate(rule).model_dump()
    rule_dict["device_ids"] = [d.id for d in rule.devices]
    
    return {"data": rule_dict}


@router.patch("/rules/{rule_id}", response_model=dict)
async def update_rule(
    rule_id: int,
    rule_data: RuleUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a rule.
    
    Returns 404 if rule not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    rule = await rule_repo.update(
        db, factory_id, rule_id,
        rule_data.model_dump(exclude_unset=True)
    )
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    logger.info(
        "rule.updated",
        factory_id=factory_id,
        rule_id=rule_id,
        user_id=user.id
    )
    
    # Build response
    rule_dict = RuleResponse.model_validate(rule).model_dump()
    rule_dict["device_ids"] = [d.id for d in rule.devices]
    
    return {"data": rule_dict}


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a rule.
    
    Returns 404 if rule not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    deleted = await rule_repo.delete(db, factory_id, rule_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    logger.info(
        "rule.deleted",
        factory_id=factory_id,
        rule_id=rule_id,
        user_id=user.id
    )


@router.patch("/rules/{rule_id}/toggle", response_model=dict)
async def toggle_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle rule active status.
    
    Returns 404 if rule not found or belongs to different factory.
    """
    factory_id = user._token_factory_id
    
    rule = await rule_repo.toggle(db, factory_id, rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    logger.info(
        "rule.toggled",
        factory_id=factory_id,
        rule_id=rule_id,
        is_active=rule.is_active,
        user_id=user.id
    )
    
    # Build response
    rule_dict = RuleResponse.model_validate(rule).model_dump()
    rule_dict["device_ids"] = [d.id for d in rule.devices]
    
    return {"data": rule_dict}
