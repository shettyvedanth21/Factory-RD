"""
Prometheus metrics endpoint.
Exposes application metrics for Prometheus scraping.
"""
from fastapi import APIRouter, Response
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)

router = APIRouter(tags=["Metrics"])

# Counters
telemetry_messages_total = Counter(
    "factoryops_telemetry_messages_total",
    "Total telemetry messages received",
    ["factory_id"]
)

alerts_triggered_total = Counter(
    "factoryops_alerts_triggered_total",
    "Total alerts triggered",
    ["factory_id", "severity"]
)

notifications_sent_total = Counter(
    "factoryops_notifications_sent_total",
    "Total notifications sent",
    ["channel", "status"]
)

celery_tasks_total = Counter(
    "factoryops_celery_tasks_total",
    "Total Celery tasks executed",
    ["queue", "status"]
)

# Histograms
api_request_duration_seconds = Histogram(
    "factoryops_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint", "status_code"]
)

telemetry_write_latency_seconds = Histogram(
    "factoryops_telemetry_write_latency_seconds",
    "Telemetry write latency to InfluxDB in seconds"
)

kpi_query_latency_seconds = Histogram(
    "factoryops_kpi_query_latency_seconds",
    "KPI query latency from InfluxDB in seconds"
)

# Gauges
active_rules_total = Gauge(
    "factoryops_active_rules_total",
    "Total number of active rules",
    ["factory_id"]
)

active_devices_total = Gauge(
    "factoryops_active_devices_total",
    "Total number of active devices",
    ["factory_id"]
)


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus text format.
    No authentication required - designed for Prometheus scraper.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
