"""
Rule engine tasks for evaluating rules against telemetry data.
"""
import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models import Rule, Device
from app.repositories import alert_repo


logger = get_logger(__name__)


# Operator functions for condition evaluation
OPERATORS = {
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
}


def evaluate_conditions(condition_tree: dict, metrics: dict) -> bool:
    """
    Recursively evaluates condition tree against metrics.
    
    Returns False (not exception) on any invalid input.
    This is a pure function with no side effects.
    
    Args:
        condition_tree: Condition tree dictionary with operator and conditions
        metrics: Dictionary of parameter keys to values
    
    Returns:
        True if conditions match, False otherwise (including errors)
    
    Examples:
        >>> evaluate_conditions({"operator": "AND", "conditions": [
        ...     {"parameter": "temp", "operator": "gt", "value": 50}
        ... ]}, {"temp": 60})
        True
        
        >>> evaluate_conditions({"operator": "OR", "conditions": [
        ...     {"parameter": "temp", "operator": "gt", "value": 100},
        ...     {"parameter": "pressure", "operator": "lt", "value": 50}
        ... ]}, {"temp": 60, "pressure": 30})
        True
    """
    try:
        op = condition_tree.get("operator", "AND").upper()
        conditions = condition_tree.get("conditions", [])
        
        if not conditions:
            return False
        
        results = []
        for cond in conditions:
            # Recursive case: nested condition tree
            if "conditions" in cond:
                results.append(evaluate_conditions(cond, metrics))
            # Base case: leaf condition
            else:
                param = cond.get("parameter")
                if param not in metrics:
                    results.append(False)
                    continue
                
                operator_func = OPERATORS.get(cond.get("operator"))
                if not operator_func:
                    results.append(False)
                    continue
                
                results.append(operator_func(float(metrics[param]), float(cond["value"])))
        
        if op == "AND":
            return all(results)
        if op == "OR":
            return any(results)
        
        return False
    
    except Exception:
        return False


def is_rule_scheduled(rule: dict, now: datetime) -> bool:
    """
    Check if rule is active according to its schedule.
    
    Args:
        rule: Rule dictionary with schedule_type and schedule_config
        now: Current datetime
    
    Returns:
        True if rule should be evaluated now, False otherwise
    """
    schedule_type = rule.get("schedule_type", "always")
    
    if schedule_type == "always":
        return True
    
    config = rule.get("schedule_config", {})
    
    if schedule_type == "time_window":
        try:
            start_time = datetime.strptime(config["start_time"], "%H:%M").time()
            end_time = datetime.strptime(config["end_time"], "%H:%M").time()
            
            # Check day of week (1=Monday, 7=Sunday)
            days = config.get("days", list(range(1, 8)))
            day_ok = now.isoweekday() in days
            
            # Check time of day
            time_ok = start_time <= now.time() <= end_time
            
            return day_ok and time_ok
        except Exception:
            return True
    
    if schedule_type == "date_range":
        try:
            start_date = datetime.fromisoformat(config["start_date"]).date()
            end_date = datetime.fromisoformat(config["end_date"]).date()
            return start_date <= now.date() <= end_date
        except Exception:
            return True
    
    return True


async def is_in_cooldown(db, rule_id: int, device_id: int, cooldown_minutes: int) -> bool:
    """
    Check if rule is in cooldown period for a device.
    
    Args:
        db: Database session
        rule_id: Rule ID
        device_id: Device ID
        cooldown_minutes: Cooldown period in minutes
    
    Returns:
        True if in cooldown, False otherwise
    """
    if cooldown_minutes == 0:
        return False
    
    cooldown = await alert_repo.get_cooldown(db, rule_id, device_id)
    if not cooldown:
        return False
    
    elapsed_seconds = (datetime.utcnow() - cooldown.last_triggered).total_seconds()
    return elapsed_seconds < (cooldown_minutes * 60)


def build_alert_message(rule_name: str, conditions: dict, metrics: dict) -> str:
    """
    Build human-readable alert message.
    
    Args:
        rule_name: Name of the rule
        conditions: Condition tree
        metrics: Current metrics
    
    Returns:
        Human-readable message
    
    Example:
        >>> build_alert_message("High Voltage", {"operator": "AND", "conditions": [
        ...     {"parameter": "voltage", "operator": "gt", "value": 240}
        ... ]}, {"voltage": 245.2})
        '[High Voltage] voltage (245.2) gt 240'
    """
    parts = []
    for cond in conditions.get("conditions", []):
        if "parameter" in cond:
            actual = metrics.get(cond["parameter"], "?")
            parts.append(f"{cond['parameter']} ({actual}) {cond['operator']} {cond['value']}")
    
    message = " AND ".join(parts) if parts else "Condition triggered"
    return f"[{rule_name}] {message}"


# Sync wrappers for Celery tasks
def get_active_rules_for_device_sync(factory_id: int, device_id: int) -> list[dict]:
    """Get active rules for a device (sync wrapper)."""
    async def _get():
        async with AsyncSessionLocal() as db:
            from app.repositories import rule_repo
            rules = await rule_repo.get_active_for_device(db, factory_id, device_id)
            # Convert to dicts
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "conditions": r.conditions,
                    "cooldown_minutes": r.cooldown_minutes,
                    "severity": r.severity.value,
                    "schedule_type": r.schedule_type.value,
                    "schedule_config": r.schedule_config,
                    "notification_channels": r.notification_channels,
                }
                for r in rules
            ]
    return asyncio.run(_get())


def is_in_cooldown_sync(rule_id: int, device_id: int, cooldown_minutes: int) -> bool:
    """Check cooldown (sync wrapper)."""
    async def _check():
        async with AsyncSessionLocal() as db:
            return await is_in_cooldown(db, rule_id, device_id, cooldown_minutes)
    return asyncio.run(_check())


def create_alert_sync(factory_id: int, rule_id: int, device_id: int,
                     triggered_at: datetime, severity: str, message: str,
                     snapshot: dict) -> int:
    """Create alert (sync wrapper)."""
    async def _create():
        async with AsyncSessionLocal() as db:
            alert = await alert_repo.create_alert(
                db, factory_id, rule_id, device_id, triggered_at,
                severity, message, snapshot
            )
            return alert.id
    return asyncio.run(_create())


def upsert_cooldown_sync(rule_id: int, device_id: int, last_triggered: datetime) -> None:
    """Upsert cooldown (sync wrapper)."""
    async def _upsert():
        async with AsyncSessionLocal() as db:
            await alert_repo.upsert_cooldown(db, rule_id, device_id, last_triggered)
    asyncio.run(_upsert())


@celery_app.task(name="evaluate_rules", bind=True, max_retries=3,
                autoretry_for=(Exception,), retry_backoff=True)
def evaluate_rules_task(self, factory_id: int, device_id: int,
                       metrics: dict, timestamp: str):
    """
    Evaluate all active rules for a device against telemetry data.
    
    This task is dispatched from the telemetry ingestion pipeline.
    It evaluates rules, respects cooldowns, creates alerts, and triggers notifications.
    
    Args:
        factory_id: Factory ID for isolation
        device_id: Device ID
        metrics: Dictionary of parameter keys to values
        timestamp: ISO format timestamp string
    
    Note:
        Continues evaluating all rules even if one fails.
        One bad rule must not affect others.
    """
    from app.workers.notifications import send_notifications_task
    
    try:
        # Get active rules for this device
        rules = get_active_rules_for_device_sync(factory_id, device_id)
        ts = datetime.fromisoformat(timestamp)
        
        logger.info(
            "rule.evaluation_started",
            factory_id=factory_id,
            device_id=device_id,
            rule_count=len(rules)
        )
        
        for rule in rules:
            try:
                # Check schedule
                if not is_rule_scheduled(rule, ts):
                    logger.debug(
                        "rule.skipped_not_scheduled",
                        factory_id=factory_id,
                        rule_id=rule["id"]
                    )
                    continue
                
                # Check cooldown
                if is_in_cooldown_sync(rule["id"], device_id, rule["cooldown_minutes"]):
                    logger.debug(
                        "rule.skipped_cooldown",
                        factory_id=factory_id,
                        rule_id=rule["id"]
                    )
                    continue
                
                # Evaluate conditions
                if evaluate_conditions(rule["conditions"], metrics):
                    # Create alert
                    alert_id = create_alert_sync(
                        factory_id=factory_id,
                        rule_id=rule["id"],
                        device_id=device_id,
                        triggered_at=ts,
                        severity=rule["severity"],
                        message=build_alert_message(rule["name"], rule["conditions"], metrics),
                        snapshot=metrics,
                    )
                    
                    # Update cooldown
                    upsert_cooldown_sync(rule["id"], device_id, ts)
                    
                    # Trigger notifications (async)
                    send_notifications_task.delay(
                        alert_id=alert_id,
                        channels=rule["notification_channels"],
                    )
                    
                    logger.info(
                        "alert.triggered",
                        factory_id=factory_id,
                        device_id=device_id,
                        rule_id=rule["id"],
                        alert_id=alert_id,
                        severity=rule["severity"]
                    )
            
            except Exception as e:
                logger.error(
                    "rule.evaluation_error",
                    factory_id=factory_id,
                    rule_id=rule.get("id"),
                    error=str(e),
                    exc_info=True
                )
                # Continue to next rule - one failure must not affect others
                continue
    
    except Exception as e:
        logger.error(
            "rule.evaluation_failed",
            factory_id=factory_id,
            device_id=device_id,
            error=str(e),
            exc_info=True
        )
        raise
