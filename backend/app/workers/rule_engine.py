"""
Rule engine tasks - placeholder for Phase 4.
This stub is needed for the telemetry pipeline to dispatch tasks.
"""
from .celery_app import celery_app


@celery_app.task(name="app.workers.rule_engine.evaluate_rules_task")
def evaluate_rules_task(factory_id: int, device_id: int, metrics: dict, timestamp: str):
    """
    Evaluate rules for a device's telemetry data.
    
    Args:
        factory_id: Factory ID for isolation
        device_id: Device ID
        metrics: Dictionary of metric keys and values
        timestamp: ISO format timestamp string
    
    Note:
        Full implementation in Phase 4.
    """
    # Placeholder - will be implemented in Phase 4
    pass
