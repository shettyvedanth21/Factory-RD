from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class KPIValue(BaseModel):
    """Single KPI value."""
    parameter_key: str
    display_name: Optional[str] = None
    unit: Optional[str] = None
    value: float
    is_stale: bool


class KPILiveResponse(BaseModel):
    """Live KPI data response."""
    device_id: int
    timestamp: datetime
    kpis: list[KPIValue]


class DataPoint(BaseModel):
    """Single time-series data point."""
    timestamp: datetime
    value: float


class KPIHistoryResponse(BaseModel):
    """Historical KPI data response."""
    parameter_key: str
    display_name: Optional[str] = None
    unit: Optional[str] = None
    interval: str
    points: list[DataPoint]
