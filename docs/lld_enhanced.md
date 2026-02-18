# Low-Level Design (LLD)
## FactoryOps AI Engineering — Device KPI Telemetry Architecture
### Version 2.0 — Agent Coding Ready

---

# 1. Purpose & Scope

This LLD provides complete implementation specifications for:

1. **Telemetry ingestion pipeline** — MQTT → InfluxDB with dynamic parameter discovery
2. **KPI management** — selection, persistence, and retrieval
3. **Dashboard data serving** — real-time cards and historical charts
4. **Rule engine evaluation** — real-time condition checking with cooldowns
5. **Analytics and reporting jobs** — async ML processing and document generation

Every section is written to be directly implementable by a coding agent without ambiguity.

---

# 2. Database Schema (MySQL)

## 2.1 Factories

```sql
CREATE TABLE factories (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(255) NOT NULL,
  slug        VARCHAR(100) NOT NULL UNIQUE,  -- used in MQTT topics
  timezone    VARCHAR(100) DEFAULT 'UTC',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 2.2 Users

```sql
CREATE TABLE users (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  factory_id      INT NOT NULL,
  email           VARCHAR(255) NOT NULL,
  whatsapp_number VARCHAR(50),
  hashed_password VARCHAR(255) NOT NULL,
  role            ENUM('super_admin', 'admin') NOT NULL DEFAULT 'admin',
  permissions     JSON,  -- {"can_create_rules": true, "can_run_analytics": false}
  is_active       BOOLEAN DEFAULT TRUE,
  invite_token    VARCHAR(255),
  invited_at      DATETIME,
  last_login      DATETIME,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_factory_email (factory_id, email),
  FOREIGN KEY (factory_id) REFERENCES factories(id)
);
```

## 2.3 Devices

```sql
CREATE TABLE devices (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  factory_id      INT NOT NULL,
  device_key      VARCHAR(100) NOT NULL,  -- matches MQTT topic segment
  name            VARCHAR(255),
  manufacturer    VARCHAR(255),
  model           VARCHAR(255),
  region          VARCHAR(255),
  api_key         VARCHAR(255),  -- device authentication key
  is_active       BOOLEAN DEFAULT TRUE,
  last_seen       DATETIME,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_factory_device (factory_id, device_key),
  FOREIGN KEY (factory_id) REFERENCES factories(id),
  INDEX idx_factory_id (factory_id)
);
```

## 2.4 Device Parameters (KPI Registry)

```sql
CREATE TABLE device_parameters (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  factory_id      INT NOT NULL,
  device_id       INT NOT NULL,
  parameter_key   VARCHAR(100) NOT NULL,   -- e.g., "voltage", "harmonic_3"
  display_name    VARCHAR(255),            -- e.g., "Voltage"
  unit            VARCHAR(50),             -- e.g., "V", "A", "Hz"
  data_type       ENUM('float', 'int', 'string') DEFAULT 'float',
  is_kpi_selected BOOLEAN DEFAULT TRUE,
  discovered_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_device_param (device_id, parameter_key),
  FOREIGN KEY (factory_id) REFERENCES factories(id),
  FOREIGN KEY (device_id) REFERENCES devices(id),
  INDEX idx_factory_device (factory_id, device_id),
  INDEX idx_device_param (device_id, parameter_key)
);
```

## 2.5 Rules

```sql
CREATE TABLE rules (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  factory_id      INT NOT NULL,
  name            VARCHAR(255) NOT NULL,
  description     TEXT,
  scope           ENUM('device', 'global') NOT NULL DEFAULT 'device',
  conditions      JSON NOT NULL,
  -- conditions format:
  -- {"operator": "AND", "conditions": [
  --   {"parameter": "voltage", "operator": "gt", "value": 240},
  --   {"parameter": "harmonic_3", "operator": "gt", "value": 8}
  -- ]}
  cooldown_minutes INT DEFAULT 15,
  is_active       BOOLEAN DEFAULT TRUE,
  schedule_type   ENUM('always', 'time_window', 'date_range') DEFAULT 'always',
  schedule_config JSON,
  -- schedule_config format:
  -- {"start_time": "08:00", "end_time": "18:00", "days": [1,2,3,4,5]}
  -- or {"start_date": "2026-01-01", "end_date": "2026-12-31"}
  severity        ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
  notification_channels JSON,
  -- {"email": true, "whatsapp": false}
  created_by      INT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (factory_id) REFERENCES factories(id),
  FOREIGN KEY (created_by) REFERENCES users(id),
  INDEX idx_factory_active (factory_id, is_active)
);
```

## 2.6 Rule-Device Mapping

```sql
CREATE TABLE rule_devices (
  rule_id    INT NOT NULL,
  device_id  INT NOT NULL,
  PRIMARY KEY (rule_id, device_id),
  FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

## 2.7 Alerts

```sql
CREATE TABLE alerts (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  factory_id      INT NOT NULL,
  rule_id         INT NOT NULL,
  device_id       INT NOT NULL,
  triggered_at    DATETIME NOT NULL,
  resolved_at     DATETIME,
  severity        ENUM('low', 'medium', 'high', 'critical') NOT NULL,
  message         TEXT,
  telemetry_snapshot JSON,  -- snapshot of metrics that triggered alert
  notification_sent BOOLEAN DEFAULT FALSE,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (factory_id) REFERENCES factories(id),
  FOREIGN KEY (rule_id) REFERENCES rules(id),
  FOREIGN KEY (device_id) REFERENCES devices(id),
  INDEX idx_factory_device_time (factory_id, device_id, triggered_at),
  INDEX idx_factory_time (factory_id, triggered_at)
);
```

## 2.8 Rule Cooldown Tracking

```sql
CREATE TABLE rule_cooldowns (
  rule_id         INT NOT NULL,
  device_id       INT NOT NULL,
  last_triggered  DATETIME NOT NULL,
  PRIMARY KEY (rule_id, device_id),
  FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

## 2.9 Analytics Jobs

```sql
CREATE TABLE analytics_jobs (
  id              VARCHAR(36) PRIMARY KEY,  -- UUID
  factory_id      INT NOT NULL,
  created_by      INT NOT NULL,
  job_type        ENUM('anomaly', 'failure_prediction', 'energy_forecast', 'ai_copilot') NOT NULL,
  mode            ENUM('standard', 'ai_copilot') DEFAULT 'standard',
  device_ids      JSON NOT NULL,
  date_range_start DATETIME NOT NULL,
  date_range_end  DATETIME NOT NULL,
  status          ENUM('pending', 'running', 'complete', 'failed') DEFAULT 'pending',
  result_url      VARCHAR(500),  -- MinIO presigned URL
  error_message   TEXT,
  started_at      DATETIME,
  completed_at    DATETIME,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (factory_id) REFERENCES factories(id),
  FOREIGN KEY (created_by) REFERENCES users(id),
  INDEX idx_factory_status (factory_id, status)
);
```

## 2.10 Reports

```sql
CREATE TABLE reports (
  id              VARCHAR(36) PRIMARY KEY,  -- UUID
  factory_id      INT NOT NULL,
  created_by      INT NOT NULL,
  title           VARCHAR(255),
  device_ids      JSON NOT NULL,
  date_range_start DATETIME NOT NULL,
  date_range_end  DATETIME NOT NULL,
  format          ENUM('pdf', 'excel', 'json') NOT NULL,
  include_analytics BOOLEAN DEFAULT FALSE,
  analytics_job_id VARCHAR(36),
  status          ENUM('pending', 'running', 'complete', 'failed') DEFAULT 'pending',
  file_url        VARCHAR(500),
  file_size_bytes BIGINT,
  error_message   TEXT,
  expires_at      DATETIME,  -- auto-cleanup after 90 days
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (factory_id) REFERENCES factories(id),
  FOREIGN KEY (created_by) REFERENCES users(id)
);
```

---

# 3. InfluxDB Schema

## 3.1 Measurement: `device_metrics`

```
Measurement: device_metrics

Tags (indexed, string):
  factory_id  = "vpc"
  device_id   = "42"      (MySQL device.id as string)
  parameter   = "voltage"

Fields (not indexed):
  value       = 231.4     (float64)

Timestamp: nanosecond precision (always UTC)
```

## 3.2 Write Example (Python)

```python
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import ASYNCHRONOUS

point = (
    Point("device_metrics")
    .tag("factory_id", str(factory_id))
    .tag("device_id", str(device_id))
    .tag("parameter", parameter_key)
    .field("value", float(value))
    .time(timestamp)
)
```

## 3.3 Query: Latest KPI Values

```flux
from(bucket: "factoryops")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => r.device_id == "{device_id}")
  |> filter(fn: (r) => contains(value: r.parameter, set: {kpi_params}))
  |> last()
```

## 3.4 Query: Historical Trend

```flux
from(bucket: "factoryops")
  |> range(start: {start}, stop: {stop})
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "{factory_id}")
  |> filter(fn: (r) => r.device_id == "{device_id}")
  |> filter(fn: (r) => r.parameter == "{parameter}")
  |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
  |> yield(name: "mean")
```

## 3.5 Retention Policies

```
Bucket: factoryops          → 180 days (raw)
Bucket: factoryops_archive  → 5 years  (aggregated, 1h windows)
```

---

# 4. Telemetry Ingestion Service

## 4.1 MQTT Topic Contract

```
factories/{factory_slug}/devices/{device_key}/telemetry
```

The telemetry service subscribes to wildcard: `factories/+/devices/+/telemetry`

## 4.2 Payload Schema

```python
class TelemetryPayload(BaseModel):
    timestamp: Optional[datetime] = None  # ISO8601; server fallback if absent
    metrics: Dict[str, Union[float, int]]  # required; string keys, numeric values

    @validator('metrics')
    def must_not_be_empty(cls, v):
        if not v:
            raise ValueError("metrics cannot be empty")
        return v
```

## 4.3 Ingestion Handler (Pseudocode)

```python
async def handle_message(topic: str, payload: bytes):
    try:
        # 1. Parse topic
        factory_slug, device_key = parse_topic(topic)

        # 2. Parse payload
        data = TelemetryPayload.model_validate_json(payload)
        timestamp = data.timestamp or datetime.utcnow()

        # 3. Resolve factory and device from DB
        factory = await get_factory_by_slug(factory_slug)
        device = await get_or_create_device(factory.id, device_key)

        # 4. Discover new parameters (upsert)
        await discover_parameters(factory.id, device.id, data.metrics)

        # 5. Write to InfluxDB (batched)
        points = build_influx_points(factory.id, device.id, data.metrics, timestamp)
        await influx_write_api.write(bucket="factoryops", record=points)

        # 6. Update device last_seen
        await update_device_last_seen(device.id, timestamp)

        # 7. Dispatch rule evaluation (non-blocking)
        evaluate_rules_task.delay(
            factory_id=factory.id,
            device_id=device.id,
            metrics=data.metrics,
            timestamp=timestamp.isoformat()
        )

    except ValidationError as e:
        logger.warning("Invalid telemetry payload", topic=topic, error=str(e))
    except Exception as e:
        logger.error("Telemetry ingestion error", topic=topic, error=str(e))
    # NEVER raise — must not crash the subscriber loop
```

## 4.4 Parameter Discovery

```python
async def discover_parameters(factory_id: int, device_id: int, metrics: dict):
    """Auto-discover and register new parameters from telemetry payload."""
    for key, value in metrics.items():
        await db.execute(
            """
            INSERT INTO device_parameters
                (factory_id, device_id, parameter_key, display_name, data_type, is_kpi_selected)
            VALUES
                (:factory_id, :device_id, :key, :display_name, :dtype, TRUE)
            ON DUPLICATE KEY UPDATE
                updated_at = NOW()
            """,
            {
                "factory_id": factory_id,
                "device_id": device_id,
                "key": key,
                "display_name": key.replace("_", " ").title(),
                "dtype": "float" if isinstance(value, float) else "int",
            }
        )
```

---

# 5. Rule Engine

## 5.1 Rule Evaluation Celery Task

```python
@celery_app.task(name="evaluate_rules", bind=True, max_retries=3)
def evaluate_rules_task(self, factory_id: int, device_id: int,
                         metrics: dict, timestamp: str):
    """
    Evaluates all active rules for a device against the current telemetry.
    Called asynchronously after every telemetry write.
    """
    try:
        rules = get_active_rules_for_device(factory_id, device_id)
        ts = datetime.fromisoformat(timestamp)

        for rule in rules:
            if not is_rule_scheduled(rule, ts):
                continue
            if is_in_cooldown(rule.id, device_id, rule.cooldown_minutes):
                continue
            if evaluate_conditions(rule.conditions, metrics):
                trigger_alert(rule, device_id, metrics, ts)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

## 5.2 Condition Evaluator

```python
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
    Recursively evaluates condition tree against metrics dict.
    condition_tree: {"operator": "AND"|"OR", "conditions": [...]}
    leaf: {"parameter": "voltage", "operator": "gt", "value": 240}
    """
    op = condition_tree.get("operator", "AND").upper()
    conditions = condition_tree.get("conditions", [])

    results = []
    for cond in conditions:
        if "conditions" in cond:
            result = evaluate_conditions(cond, metrics)
        else:
            param = cond["parameter"]
            if param not in metrics:
                result = False  # Missing param = condition not met
            else:
                fn = OPERATORS.get(cond["operator"])
                result = fn(metrics[param], cond["value"]) if fn else False
        results.append(result)

    if op == "AND":
        return all(results)
    elif op == "OR":
        return any(results)
    return False
```

## 5.3 Alert Generation

```python
def trigger_alert(rule, device_id: int, metrics: dict, timestamp: datetime):
    # 1. Create alert record
    alert_id = create_alert(
        factory_id=rule.factory_id,
        rule_id=rule.id,
        device_id=device_id,
        triggered_at=timestamp,
        severity=rule.severity,
        message=build_alert_message(rule, metrics),
        telemetry_snapshot=metrics,
    )

    # 2. Update cooldown
    upsert_cooldown(rule.id, device_id, timestamp)

    # 3. Dispatch notification
    send_notifications_task.delay(
        alert_id=alert_id,
        channels=rule.notification_channels,
    )
```

---

# 6. API Endpoints

## 6.1 Authentication

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/factories` | List all factories (public, for factory selector) |
| POST | `/api/v1/auth/login` | Login with factory_id + email + password |
| POST | `/api/v1/auth/refresh` | Refresh JWT |
| POST | `/api/v1/auth/logout` | Invalidate token |

## 6.2 Dashboard

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/dashboard/summary` | Factory summary (device counts, energy, alerts, health) |

## 6.3 Devices / Machines

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/devices` | List all devices for factory |
| GET | `/api/v1/devices/{device_id}` | Device detail + latest KPIs |
| POST | `/api/v1/devices` | Register device |
| PATCH | `/api/v1/devices/{device_id}` | Update device metadata |
| DELETE | `/api/v1/devices/{device_id}` | Deactivate device |

## 6.4 Telemetry / KPI

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/devices/{device_id}/parameters` | List all parameters for device |
| PATCH | `/api/v1/devices/{device_id}/parameters/{param_id}` | Update KPI selection / display name |
| GET | `/api/v1/devices/{device_id}/kpis/live` | Latest value for all selected KPIs |
| GET | `/api/v1/devices/{device_id}/kpis/history` | Historical trend for a parameter |

**KPI live query params:** none

**KPI history query params:**
- `parameter` (required) — parameter key
- `start` (required) — ISO8601 datetime
- `end` (required) — ISO8601 datetime
- `interval` (optional) — `1m`, `5m`, `1h`, `1d` (default: `5m`)

## 6.5 Rules

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/rules` | List rules for factory |
| POST | `/api/v1/rules` | Create rule |
| GET | `/api/v1/rules/{rule_id}` | Get rule detail |
| PATCH | `/api/v1/rules/{rule_id}` | Update rule |
| DELETE | `/api/v1/rules/{rule_id}` | Delete rule |
| PATCH | `/api/v1/rules/{rule_id}/toggle` | Enable/disable rule |

## 6.6 Alerts

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/alerts` | List alerts (filterable by device, severity, date) |
| GET | `/api/v1/alerts/{alert_id}` | Alert detail |
| PATCH | `/api/v1/alerts/{alert_id}/resolve` | Mark alert resolved |

## 6.7 Analytics

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/analytics/jobs` | Start analytics job |
| GET | `/api/v1/analytics/jobs` | List jobs for factory |
| GET | `/api/v1/analytics/jobs/{job_id}` | Get job status + results |
| DELETE | `/api/v1/analytics/jobs/{job_id}` | Cancel job |

## 6.8 Reporting

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/reports` | Generate report |
| GET | `/api/v1/reports` | List reports for factory |
| GET | `/api/v1/reports/{report_id}` | Get report status |
| GET | `/api/v1/reports/{report_id}/download` | Redirect to MinIO presigned URL |

## 6.9 Users

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users` | super_admin | List factory users |
| POST | `/api/v1/users/invite` | super_admin | Invite admin user |
| PATCH | `/api/v1/users/{user_id}/permissions` | super_admin | Update permissions |
| DELETE | `/api/v1/users/{user_id}` | super_admin | Deactivate user |
| POST | `/api/v1/users/accept-invite` | public | Accept invite + set password |

---

# 7. Frontend Architecture

## 7.1 Page Structure

```
/ → redirect to /factory-select
/factory-select → Factory selector page (public)
/login → Login page (requires factory context from query param or localStorage)
/dashboard → Main factory dashboard
/machines → Machine list
/machines/:deviceId → Device detail (KPI cards + charts)
/rules → Rules list
/rules/new → Rule builder
/rules/:ruleId → Rule detail/edit
/analytics → Analytics jobs list
/analytics/new → New analytics job
/analytics/:jobId → Job results
/reports → Reports list
/reports/new → New report
/users → User management (super_admin only)
```

## 7.2 State Management

```
Zustand stores:
  - authStore: {user, factory, token, role}
  - uiStore: {sidebar, notifications}

React Query (server state):
  - useDevices(), useDevice(id)
  - useKPIsLive(deviceId) — polling every 5s
  - useKPIHistory(deviceId, params) — on user interaction
  - useAlerts(filters)
  - useRules()
  - useAnalyticsJob(jobId) — polling when status != complete
```

## 7.3 KPI Live Polling

```typescript
// Poll every 5 seconds for live KPI data
const { data: kpis } = useQuery({
  queryKey: ['kpis', 'live', deviceId],
  queryFn: () => api.getKPIsLive(deviceId),
  refetchInterval: 5000,
  staleTime: 3000,
});
```

## 7.4 Device Detail Page Layout

```
DeviceDetailPage
├── DeviceHeader (name, model, region, status badge, last_seen)
├── KPICardGrid
│   └── KPICard[] (one per selected parameter)
│       └── value | unit | trend indicator | parameter display_name
├── TelemetryChart
│   ├── ParameterSelector (dropdown of selected KPIs)
│   ├── TimeRangeSelector (1h, 24h, 7d, 30d, custom)
│   ├── IntervalSelector (1m, 5m, 1h, 1d)
│   └── LineChart (Recharts)
└── AlertsPanel (recent alerts for this device)
```

---

# 8. Analytics Service

## 8.1 Available Analysis Types

| Type | Algorithm | Input | Output |
|---|---|---|---|
| `anomaly` | Isolation Forest | Telemetry time-series | Anomaly scores per timestamp |
| `failure_prediction` | Random Forest classifier | Telemetry features | Failure probability + timeline |
| `energy_forecast` | Prophet | Energy consumption history | Next 7/30 day forecast |
| `ai_copilot` | Auto-select | Any telemetry | Best model + narrative summary |

## 8.2 Job Processing Flow

```python
@celery_app.task(name="run_analytics_job", bind=True, max_retries=1)
def run_analytics_job(self, job_id: str):
    job = get_job(job_id)
    update_job_status(job_id, "running")

    try:
        # 1. Fetch telemetry from InfluxDB
        df = fetch_telemetry_dataframe(
            factory_id=job.factory_id,
            device_ids=job.device_ids,
            start=job.date_range_start,
            end=job.date_range_end,
        )

        # 2. Run model
        results = run_model(job.job_type, df)

        # 3. Serialize + save to MinIO
        result_url = save_results_to_minio(job_id, results, job.factory_id)

        # 4. Update job
        update_job_status(job_id, "complete", result_url=result_url)

    except Exception as e:
        update_job_status(job_id, "failed", error=str(e))
        raise self.retry(exc=e)
```

---

# 9. Notification Service

## 9.1 Channels

| Channel | Integration | Config |
|---|---|---|
| Email | SMTP (smtplib) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` |
| WhatsApp | Twilio API | `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_FROM` |

## 9.2 Notification Task

```python
@celery_app.task(name="send_notifications", bind=True, max_retries=3)
def send_notifications_task(self, alert_id: int, channels: dict):
    alert = get_alert_with_relations(alert_id)
    factory_users = get_factory_users(alert.factory_id)

    for user in factory_users:
        if channels.get("email") and user.email:
            send_email_alert(user.email, alert)
        if channels.get("whatsapp") and user.whatsapp_number:
            send_whatsapp_alert(user.whatsapp_number, alert)

    mark_notification_sent(alert_id)
```

---

# 10. Error Handling Specification

## 10.1 API Error Response Format

```json
{
  "error": {
    "code": "DEVICE_NOT_FOUND",
    "message": "Device with id 42 not found in factory vpc",
    "detail": null
  }
}
```

## 10.2 Standard HTTP Status Codes

| Status | When |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Validation error |
| 401 | Missing/invalid token |
| 403 | Valid token, insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate) |
| 422 | Request body schema error |
| 500 | Internal server error |
| 503 | Dependency unavailable |

## 10.3 Telemetry Service Error Policy

- **Malformed JSON** → log warning, skip, continue
- **Missing factory** → log error, skip, continue
- **InfluxDB timeout** → log error, increment metric, continue (data lost, acceptable)
- **MySQL error** → log error, skip parameter discovery, continue with InfluxDB write
- **MQTT disconnect** → reconnect with exponential backoff (1s, 2s, 4s, 8s, max 60s)

**The telemetry subscriber loop must NEVER raise an unhandled exception.**

---

# 11. Environment Configuration

```bash
# Database
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=factoryops
MYSQL_USER=factoryops
MYSQL_PASSWORD=secret

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=factoryops
INFLUXDB_BUCKET=factoryops

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=factoryops

# MQTT
MQTT_BROKER_HOST=emqx
MQTT_BROKER_PORT=1883

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# Notifications
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

---

# 12. Acceptance Criteria

A feature is considered complete when:

**Telemetry:**
- [ ] New device publishes MQTT → device auto-registered in MySQL
- [ ] New parameter key in payload → auto-discovered, `is_kpi_selected = TRUE`
- [ ] All metrics written to InfluxDB with correct tags
- [ ] Duplicate parameter key → no duplicate DB row (upsert)
- [ ] Malformed payload → logged, service continues without crash

**KPIs:**
- [ ] `/kpis/live` returns last value within 5-minute window per selected parameter
- [ ] `/kpis/history` returns aggregated data for requested range and interval
- [ ] KPI selection update → immediately reflected in dashboard

**Rules:**
- [ ] Rule created for single or multiple devices
- [ ] Rule condition evaluated on every telemetry event
- [ ] Alert generated when conditions met and cooldown not active
- [ ] Cooldown prevents re-trigger within configured window
- [ ] Notifications dispatched to configured channels

**Analytics:**
- [ ] Job submitted → returns job_id immediately
- [ ] Celery worker processes job in background
- [ ] Results saved to MinIO, job status updated
- [ ] Client can poll job status and download results

**Security:**
- [ ] No endpoint accessible without valid JWT
- [ ] No cross-factory data leakage (automated test)
- [ ] Super Admin operations rejected for Admin role

---

*End of LLD v2.0*
