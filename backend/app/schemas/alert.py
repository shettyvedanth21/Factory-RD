from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AlertResponse(BaseModel):
    """Alert details response."""
    id: int
    rule_id: int
    rule_name: str
    device_id: int
    device_name: Optional[str] = None
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    severity: str
    message: Optional[str] = None
    telemetry_snapshot: Optional[dict] = None
    notification_sent: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
