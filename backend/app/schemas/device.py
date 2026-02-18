from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DeviceCreate(BaseModel):
    """Schema for creating a new device."""
    device_key: str
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    region: Optional[str] = None


class DeviceUpdate(BaseModel):
    """Schema for updating a device."""
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    region: Optional[str] = None
    is_active: Optional[bool] = None


class DeviceResponse(BaseModel):
    """Full device details response."""
    id: int
    device_key: str
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    region: Optional[str] = None
    api_key: Optional[str] = None
    is_active: bool
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    parameters: list = []  # Will be populated with ParameterResponse objects
    
    class Config:
        from_attributes = True


class DeviceListItem(BaseModel):
    """Device list item with computed fields."""
    id: int
    device_key: str
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    region: Optional[str] = None
    is_active: bool
    last_seen: Optional[datetime] = None
    health_score: int
    active_alert_count: int
    current_energy_kw: float
    
    class Config:
        from_attributes = True
