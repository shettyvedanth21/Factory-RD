from celery import Celery

from app.core.config import settings


# Create Celery app instance
celery_app = Celery("factoryops")

# Configure Celery
celery_app.config_from_object({
    # Broker and backend
    "broker_url": settings.celery_broker_url,
    "result_backend": settings.celery_result_backend,
    
    # Serialization
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    
    # Task routing to specialized queues
    "task_routes": {
        "app.workers.rule_engine.evaluate_rules_task": {"queue": "rule_engine"},
        "app.workers.analytics.run_analytics_job": {"queue": "analytics"},
        "app.workers.reporting.generate_report": {"queue": "reporting"},
        "app.workers.notifications.send_notifications": {"queue": "notifications"},
    },
    
    # Reliability settings
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    
    # Time limits
    "task_time_limit": 3600,  # 1 hour hard limit
    "task_soft_time_limit": 3300,  # 55 minutes soft limit
    
    # Result expiration
    "result_expires": 86400,  # 24 hours
})
