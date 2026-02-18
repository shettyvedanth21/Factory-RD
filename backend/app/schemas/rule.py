from datetime import datetime
from typing import Optional, Literal, Union
from pydantic import BaseModel, Field


class ConditionLeaf(BaseModel):
    """Leaf condition for rule evaluation."""
    parameter: str
    operator: Literal["gt", "lt", "gte", "lte", "eq", "neq"]
    value: float


class ConditionTree(BaseModel):
    """Tree condition with AND/OR logic."""
    operator: Literal["AND", "OR"]
    conditions: list[Union["ConditionLeaf", "ConditionTree"]]


# Enable recursive model
ConditionTree.model_rebuild()


class RuleCreate(BaseModel):
    """Schema for creating a new rule."""
    name: str
    description: Optional[str] = None
    scope: Literal["device", "global"]
    device_ids: list[int] = Field(default_factory=list)
    conditions: ConditionTree
    cooldown_minutes: int = Field(default=15, ge=0)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    schedule_type: Literal["always", "time_window", "date_range"] = "always"
    schedule_config: Optional[dict] = None
    notification_channels: Optional[dict] = Field(default_factory=lambda: {"email": False, "whatsapp": False})


class RuleUpdate(BaseModel):
    """Schema for updating a rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[Literal["device", "global"]] = None
    device_ids: Optional[list[int]] = None
    conditions: Optional[ConditionTree] = None
    cooldown_minutes: Optional[int] = None
    severity: Optional[Literal["low", "medium", "high", "critical"]] = None
    schedule_type: Optional[Literal["always", "time_window", "date_range"]] = None
    schedule_config: Optional[dict] = None
    notification_channels: Optional[dict] = None
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    """Full rule details response."""
    id: int
    name: str
    description: Optional[str] = None
    scope: str
    device_ids: list[int]
    conditions: dict
    cooldown_minutes: int
    is_active: bool
    schedule_type: str
    schedule_config: Optional[dict] = None
    severity: str
    notification_channels: Optional[dict] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
