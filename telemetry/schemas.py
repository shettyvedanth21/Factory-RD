from datetime import datetime
from typing import Dict, Union, Optional

from pydantic import BaseModel, model_validator


class TelemetryPayload(BaseModel):
    """
    Telemetry payload schema for MQTT messages.
    
    Example:
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "metrics": {
                "temperature": 45.5,
                "pressure": 101.3,
                "rpm": 1500
            }
        }
    """
    timestamp: Optional[datetime] = None
    metrics: Dict[str, Union[float, int]]
    
    @model_validator(mode='after')
    def validate_metrics(self):
        """
        Validate that metrics is non-empty and contains only numeric values.
        """
        if not self.metrics:
            raise ValueError("metrics cannot be empty")
        
        for key, value in self.metrics.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"metric '{key}' must be numeric, got {type(value).__name__}")
        
        return self


def parse_topic(topic: str) -> tuple[str, str]:
    """
    Parse MQTT topic to extract factory slug and device key.
    
    Expected format: "factories/{factory_slug}/devices/{device_key}/telemetry"
    
    Args:
        topic: MQTT topic string
    
    Returns:
        Tuple of (factory_slug, device_key)
    
    Raises:
        ValueError: If topic format is invalid
    
    Examples:
        >>> parse_topic("factories/vpc/devices/M01/telemetry")
        ('vpc', 'M01')
        
        >>> parse_topic("invalid/topic")
        ValueError: Invalid topic format: invalid/topic
    """
    parts = topic.split("/")
    
    if len(parts) != 5:
        raise ValueError(f"Invalid topic format: {topic}")
    
    if parts[0] != "factories":
        raise ValueError(f"Invalid topic format: {topic}")
    
    if parts[2] != "devices":
        raise ValueError(f"Invalid topic format: {topic}")
    
    if parts[4] != "telemetry":
        raise ValueError(f"Invalid topic format: {topic}")
    
    factory_slug = parts[1]
    device_key = parts[3]
    
    return factory_slug, device_key
