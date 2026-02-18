"""
Notification tasks for sending alerts via email and WhatsApp.
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from sqlalchemy import select, update as sql_update
from twilio.rest import Client as TwilioClient

from .celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.logging import get_logger
from app.models import Alert, Rule, Device, User


logger = get_logger(__name__)


def get_alert_with_relations_sync(alert_id: int) -> Optional[dict]:
    """Get alert with rule and device details (sync wrapper)."""
    async def _get():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Alert).where(Alert.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            
            if not alert:
                return None
            
            # Get rule
            rule_result = await db.execute(
                select(Rule).where(Rule.id == alert.rule_id)
            )
            rule = rule_result.scalar_one_or_none()
            
            # Get device
            device_result = await db.execute(
                select(Device).where(Device.id == alert.device_id)
            )
            device = device_result.scalar_one_or_none()
            
            return {
                "id": alert.id,
                "factory_id": alert.factory_id,
                "rule_name": rule.name if rule else "Unknown Rule",
                "device_name": device.name if device else device.device_key if device else "Unknown Device",
                "device_key": device.device_key if device else "Unknown",
                "severity": alert.severity.value,
                "message": alert.message,
                "triggered_at": alert.triggered_at,
                "telemetry_snapshot": alert.telemetry_snapshot or {},
            }
    
    return asyncio.run(_get())


def get_factory_users_sync(factory_id: int) -> list[dict]:
    """Get all users for a factory (sync wrapper)."""
    async def _get():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(
                    User.factory_id == factory_id,
                    User.is_active == True
                )
            )
            users = result.scalars().all()
            
            return [
                {
                    "email": u.email,
                    "whatsapp_number": u.whatsapp_number,
                }
                for u in users
            ]
    
    return asyncio.run(_get())


def mark_notification_sent_sync(alert_id: int) -> None:
    """Mark alert as notification sent (sync wrapper)."""
    async def _mark():
        async with AsyncSessionLocal() as db:
            await db.execute(
                sql_update(Alert)
                .where(Alert.id == alert_id)
                .values(notification_sent=True)
            )
            await db.commit()
    
    asyncio.run(_mark())


def send_email(to_email: str, alert: dict) -> None:
    """
    Send email notification.
    
    Skips gracefully if SMTP not configured.
    
    Args:
        to_email: Recipient email
        alert: Alert dictionary
    """
    # Skip if SMTP not configured
    if not settings.smtp_host:
        logger.debug("notification.email_skipped_not_configured")
        return
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg["Subject"] = f"[{alert['severity'].upper()}] Alert: {alert['rule_name']}"
        
        # Email body
        body = f"""
Alert Notification

Rule: {alert['rule_name']}
Device: {alert['device_name']} ({alert['device_key']})
Severity: {alert['severity'].upper()}
Triggered: {alert['triggered_at']}

Message:
{alert['message']}

Telemetry Snapshot:
{alert['telemetry_snapshot']}
"""
        
        msg.attach(MIMEText(body, "plain"))
        
        # Send email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_user and settings.smtp_password:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
            
            server.send_message(msg)
        
        # Mask email for privacy
        masked_email = to_email[:3] + "***" + to_email[to_email.index("@"):]
        
        # Increment Prometheus counter
        try:
            from app.api.v1.metrics import notifications_sent_total
            notifications_sent_total.labels(channel="email", status="success").inc()
        except Exception:
            pass
        
        logger.info(
            "notification.email_sent",
            alert_id=alert["id"],
            to_email=masked_email,
            factory_id=alert["factory_id"],
            channel="email",
            success=True
        )
    
    except Exception as e:
        # Mask email for privacy
        masked_email = to_email[:3] + "***" + to_email[to_email.index("@"):] if "@" in to_email else to_email
        
        # Increment Prometheus counter
        try:
            from app.api.v1.metrics import notifications_sent_total
            notifications_sent_total.labels(channel="email", status="failure").inc()
        except Exception:
            pass
        
        logger.error(
            "notification.email_failed",
            alert_id=alert["id"],
            to_email=masked_email,
            factory_id=alert["factory_id"],
            channel="email",
            success=False,
            error=str(e)
        )


def send_whatsapp(to_number: str, alert: dict) -> None:
    """
    Send WhatsApp notification via Twilio.
    
    Skips gracefully if Twilio not configured.
    
    Args:
        to_number: Recipient WhatsApp number (E.164 format)
        alert: Alert dictionary
    """
    # Skip if Twilio not configured
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.debug("notification.whatsapp_skipped_not_configured")
        return
    
    try:
        # Create Twilio client
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        
        # Format message
        message_body = f"""
🚨 *{alert['severity'].upper()} ALERT*

*Rule:* {alert['rule_name']}
*Device:* {alert['device_name']}
*Time:* {alert['triggered_at']}

{alert['message']}
"""
        
        # Send WhatsApp message
        message = client.messages.create(
            from_=f"whatsapp:{settings.twilio_whatsapp_from}",
            to=f"whatsapp:{to_number}",
            body=message_body
        )
        
        # Mask phone number for privacy
        masked_number = to_number[:4] + "***" + to_number[-3:] if len(to_number) > 7 else to_number
        
        # Increment Prometheus counter
        try:
            from app.api.v1.metrics import notifications_sent_total
            notifications_sent_total.labels(channel="whatsapp", status="success").inc()
        except Exception:
            pass
        
        logger.info(
            "notification.whatsapp_sent",
            alert_id=alert["id"],
            to_number=masked_number,
            message_sid=message.sid,
            factory_id=alert["factory_id"],
            channel="whatsapp",
            success=True
        )
    
    except Exception as e:
        # Mask phone number for privacy
        masked_number = to_number[:4] + "***" + to_number[-3:] if len(to_number) > 7 else to_number
        
        # Increment Prometheus counter
        try:
            from app.api.v1.metrics import notifications_sent_total
            notifications_sent_total.labels(channel="whatsapp", status="failure").inc()
        except Exception:
            pass
        
        logger.error(
            "notification.whatsapp_failed",
            alert_id=alert["id"],
            to_number=masked_number,
            factory_id=alert["factory_id"],
            channel="whatsapp",
            success=False,
            error=str(e)
        )


@celery_app.task(name="send_notifications", bind=True, max_retries=3,
                autoretry_for=(Exception,), retry_backoff=True)
def send_notifications_task(self, alert_id: int, channels: dict):
    """
    Send notifications for an alert.
    
    Sends to all active users in the factory via configured channels.
    Failures in one channel don't affect others.
    
    Args:
        alert_id: Alert ID
        channels: Dictionary of channels {"email": bool, "whatsapp": bool}
    """
    import time
    start_time = time.time()
    
    try:
        # Get alert details
        alert = get_alert_with_relations_sync(alert_id)
        if not alert:
            logger.warning("notification.alert_not_found", alert_id=alert_id)
            return
        
        # Get factory users
        users = get_factory_users_sync(alert["factory_id"])
        
        logger.info(
            "notification.started",
            alert_id=alert_id,
            factory_id=alert["factory_id"],
            user_count=len(users),
            channels=channels
        )
        
        # Send notifications
        for user in users:
            # Email
            if channels.get("email") and user["email"]:
                try:
                    send_email(user["email"], alert)
                except Exception as e:
                    logger.error(
                        "notification.user_email_failed",
                        alert_id=alert_id,
                        email=user["email"],
                        error=str(e)
                    )
            
            # WhatsApp
            if channels.get("whatsapp") and user["whatsapp_number"]:
                try:
                    send_whatsapp(user["whatsapp_number"], alert)
                except Exception as e:
                    logger.error(
                        "notification.user_whatsapp_failed",
                        alert_id=alert_id,
                        whatsapp=user["whatsapp_number"],
                        error=str(e)
                    )
        
        # Mark as sent
        mark_notification_sent_sync(alert_id)
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "notification.completed",
            alert_id=alert_id,
            factory_id=alert["factory_id"],
            duration_ms=round(duration_ms, 2),
            user_count=len(users),
            channels=list(channels.keys())
        )
    
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        logger.error(
            "notification.task_failed",
            alert_id=alert_id,
            duration_ms=round(duration_ms, 2),
            error=str(e),
            exc_info=True
        )
        raise
