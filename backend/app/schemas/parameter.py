from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ParameterResponse(BaseModel):
    """Parameter details response."""
    id: int
    parameter_key: str
    display_name: Optional[str] = None
    unit: Optional[str] = None
    data_type: str
    is_kpi_selected: bool
    discovered_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ParameterUpdate(BaseModel):
    """Schema for updating a parameter."""
    display_name: Optional[str] = None
    unit: Optional[str] = None
    is_kpi_selected: Optional[bool] = None
