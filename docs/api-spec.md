# API Specification
## FactoryOps AI Engineering — REST API v1
### Complete Endpoint Reference

---

## Base URL

```
Development:  http://localhost:8000/api/v1
Production:   https://{domain}/api/v1
```

## Authentication

All endpoints (except `/factories`, `/auth/login`, `/users/accept-invite`) require:

```
Authorization: Bearer <jwt_token>
```

JWT payload structure:
```json
{
  "sub": "42",
  "factory_id": 1,
  "factory_slug": "vpc",
  "role": "super_admin",
  "exp": 1740000000
}
```

---

## 1. Factory & Auth

### GET /factories
List all factories (public endpoint — used for factory selector page).

**Response 200:**
```json
{
  "data": [
    { "id": 1, "name": "VPC Factory", "slug": "vpc" },
    { "id": 2, "name": "Chennai Plant", "slug": "chennai" }
  ]
}
```

---

### POST /auth/login
Authenticate user within a factory context.

**Request:**
```json
{
  "factory_id": 1,
  "email": "admin@vpc.com",
  "password": "secret123"
}
```

**Response 200:**
```json
{
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": 42,
      "email": "admin@vpc.com",
      "role": "super_admin",
      "permissions": {}
    }
  }
}
```

**Response 401:**
```json
{ "error": { "code": "INVALID_CREDENTIALS", "message": "Invalid email or password" } }
```

---

### POST /auth/refresh
Refresh access token.

**Response 200:** same as `/auth/login` response

---

## 2. Dashboard

### GET /dashboard/summary
Factory-level operational summary.

**Response 200:**
```json
{
  "data": {
    "total_devices": 24,
    "active_devices": 21,
    "offline_devices": 3,
    "current_energy_kw": 142.7,
    "active_alerts": 5,
    "critical_alerts": 1,
    "health_score": 87,
    "energy_today_kwh": 1423.5,
    "energy_this_month_kwh": 38420.1
  }
}
```

---

## 3. Devices / Machines

### GET /devices
List all devices for the authenticated factory.

**Query params:**
- `page` (int, default 1)
- `per_page` (int, default 20, max 100)
- `search` (string) — filter by name or device_key
- `is_active` (bool)

**Response 200:**
```json
{
  "data": [
    {
      "id": 5,
      "device_key": "M01",
      "name": "Compressor 1",
      "manufacturer": "Siemens",
      "model": "SIMOTICS",
      "region": "Zone A",
      "is_active": true,
      "last_seen": "2026-03-01T10:01:02Z",
      "health_score": 92,
      "current_energy_kw": 12.4,
      "active_alert_count": 0
    }
  ],
  "total": 24,
  "page": 1,
  "per_page": 20
}
```

---

### GET /devices/{device_id}
Device detail with latest KPI snapshot.

**Response 200:**
```json
{
  "data": {
    "id": 5,
    "device_key": "M01",
    "name": "Compressor 1",
    "manufacturer": "Siemens",
    "model": "SIMOTICS",
    "region": "Zone A",
    "is_active": true,
    "last_seen": "2026-03-01T10:01:02Z",
    "health_score": 92,
    "parameters": [
      {
        "id": 12,
        "parameter_key": "voltage",
        "display_name": "Voltage",
        "unit": "V",
        "is_kpi_selected": true
      }
    ]
  }
}
```

---

### POST /devices
Register a new device.

**Request:**
```json
{
  "device_key": "M05",
  "name": "Pump 5",
  "manufacturer": "ABB",
  "model": "IRB-120",
  "region": "Zone B"
}
```

**Response 201:**
```json
{ "data": { "id": 25, "device_key": "M05", "api_key": "dk_abc123..." } }
```

---

### PATCH /devices/{device_id}
Update device metadata.

**Request (partial):**
```json
{ "name": "Pump 5 Updated", "region": "Zone C" }
```

**Response 200:** Updated device object

---

## 4. Parameters / KPIs

### GET /devices/{device_id}/parameters
List all discovered parameters for a device.

**Response 200:**
```json
{
  "data": [
    {
      "id": 12,
      "parameter_key": "voltage",
      "display_name": "Voltage",
      "unit": "V",
      "data_type": "float",
      "is_kpi_selected": true,
      "discovered_at": "2026-02-15T08:00:00Z"
    }
  ]
}
```

---

### PATCH /devices/{device_id}/parameters/{param_id}
Update parameter display name, unit, or KPI selection.

**Request:**
```json
{
  "display_name": "Line Voltage",
  "unit": "V",
  "is_kpi_selected": false
}
```

**Response 200:** Updated parameter object

---

### GET /devices/{device_id}/kpis/live
Latest values for all KPI-selected parameters.

**Response 200:**
```json
{
  "data": {
    "device_id": 5,
    "timestamp": "2026-03-01T10:01:02Z",
    "kpis": [
      {
        "parameter_key": "voltage",
        "display_name": "Voltage",
        "unit": "V",
        "value": 231.4,
        "is_stale": false
      },
      {
        "parameter_key": "current",
        "display_name": "Current",
        "unit": "A",
        "value": 3.2,
        "is_stale": false
      }
    ]
  }
}
```

Note: `is_stale: true` when last value is older than 10 minutes.

---

### GET /devices/{device_id}/kpis/history
Historical trend data for a single parameter.

**Query params:**
- `parameter` (required) — parameter key e.g. `voltage`
- `start` (required) — ISO8601 datetime
- `end` (required) — ISO8601 datetime
- `interval` (optional) — `1m`, `5m`, `1h`, `1d` (default: auto-selected based on range)

**Response 200:**
```json
{
  "data": {
    "parameter_key": "voltage",
    "display_name": "Voltage",
    "unit": "V",
    "interval": "5m",
    "points": [
      { "timestamp": "2026-03-01T10:00:00Z", "value": 231.2 },
      { "timestamp": "2026-03-01T10:05:00Z", "value": 231.8 }
    ]
  }
}
```

---

## 5. Rules

### GET /rules
List rules for the factory.

**Query params:**
- `device_id` (int) — filter by device
- `is_active` (bool)
- `scope` — `device` | `global`
- `page`, `per_page`

**Response 200:**
```json
{
  "data": [
    {
      "id": 7,
      "name": "Overvoltage Alert",
      "scope": "device",
      "is_active": true,
      "severity": "high",
      "cooldown_minutes": 15,
      "conditions": {
        "operator": "AND",
        "conditions": [
          { "parameter": "voltage", "operator": "gt", "value": 240 }
        ]
      },
      "device_ids": [5, 8],
      "created_at": "2026-02-01T00:00:00Z"
    }
  ],
  "total": 12
}
```

---

### POST /rules
Create a new rule.

**Request:**
```json
{
  "name": "High Voltage + Harmonic",
  "description": "Alert when voltage > 240V and harmonic_3 > 8",
  "scope": "device",
  "device_ids": [5],
  "conditions": {
    "operator": "AND",
    "conditions": [
      { "parameter": "voltage", "operator": "gt", "value": 240 },
      { "parameter": "harmonic_3", "operator": "gt", "value": 8 }
    ]
  },
  "cooldown_minutes": 15,
  "severity": "high",
  "schedule_type": "always",
  "notification_channels": { "email": true, "whatsapp": false }
}
```

**Supported operators:** `gt`, `lt`, `gte`, `lte`, `eq`, `neq`

**Response 201:** Created rule object

---

### PATCH /rules/{rule_id}/toggle
Enable or disable a rule.

**Response 200:**
```json
{ "data": { "id": 7, "is_active": false } }
```

---

## 6. Alerts

### GET /alerts
List alerts for the factory.

**Query params:**
- `device_id` (int)
- `severity` — `low` | `medium` | `high` | `critical`
- `resolved` (bool) — filter resolved/unresolved
- `start`, `end` (ISO8601)
- `page`, `per_page`

**Response 200:**
```json
{
  "data": [
    {
      "id": 101,
      "rule_id": 7,
      "rule_name": "Overvoltage Alert",
      "device_id": 5,
      "device_name": "Compressor 1",
      "triggered_at": "2026-03-01T10:01:02Z",
      "resolved_at": null,
      "severity": "high",
      "message": "Voltage (245.2V) exceeded threshold (240V)",
      "telemetry_snapshot": { "voltage": 245.2, "current": 3.8 }
    }
  ],
  "total": 35
}
```

---

### PATCH /alerts/{alert_id}/resolve
Mark alert as resolved.

**Response 200:**
```json
{ "data": { "id": 101, "resolved_at": "2026-03-01T10:30:00Z" } }
```

---

## 7. Analytics

### POST /analytics/jobs
Start an analytics job. Returns immediately with job ID.

**Request:**
```json
{
  "job_type": "anomaly",
  "mode": "standard",
  "device_ids": [5, 8],
  "date_range_start": "2026-02-01T00:00:00Z",
  "date_range_end": "2026-03-01T00:00:00Z"
}
```

**job_type options:** `anomaly`, `failure_prediction`, `energy_forecast`, `ai_copilot`
**mode options:** `standard`, `ai_copilot`

**Response 202:**
```json
{
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending"
  }
}
```

---

### GET /analytics/jobs/{job_id}
Poll for job status and results.

**Response 200 (running):**
```json
{
  "data": {
    "job_id": "550e8400-...",
    "status": "running",
    "started_at": "2026-03-01T10:05:00Z"
  }
}
```

**Response 200 (complete):**
```json
{
  "data": {
    "job_id": "550e8400-...",
    "status": "complete",
    "completed_at": "2026-03-01T10:06:30Z",
    "results": {
      "summary": "3 anomalies detected in device M01 between Feb 15–18",
      "anomaly_count": 3,
      "anomaly_score": 0.82,
      "anomalies": [
        {
          "device_id": 5,
          "timestamp": "2026-02-15T14:32:00Z",
          "score": 0.94,
          "affected_parameters": ["voltage", "current"]
        }
      ]
    },
    "download_url": "https://minio.../analytics/vpc/550e8400.json?token=..."
  }
}
```

---

## 8. Reports

### POST /reports
Generate a report.

**Request:**
```json
{
  "title": "March Energy Report",
  "device_ids": [5, 8, 12],
  "date_range_start": "2026-02-01T00:00:00Z",
  "date_range_end": "2026-03-01T00:00:00Z",
  "format": "pdf",
  "include_analytics": true,
  "analytics_job_id": "550e8400-..."
}
```

**format options:** `pdf`, `excel`, `json`

**Response 202:**
```json
{ "data": { "report_id": "abc-123", "status": "pending" } }
```

---

### GET /reports/{report_id}/download
Redirect to presigned MinIO download URL.

**Response 302:** Redirect to file URL

---

## 9. Users

*All endpoints in this section require `super_admin` role.*

### GET /users
List factory users.

**Response 200:**
```json
{
  "data": [
    {
      "id": 10,
      "email": "john@vpc.com",
      "whatsapp_number": "+919876543210",
      "role": "admin",
      "is_active": true,
      "permissions": {
        "can_create_rules": true,
        "can_run_analytics": false,
        "can_generate_reports": true
      },
      "last_login": "2026-03-01T08:00:00Z"
    }
  ]
}
```

---

### POST /users/invite
Invite a new admin user.

**Request:**
```json
{
  "email": "newadmin@vpc.com",
  "whatsapp_number": "+919876543211",
  "permissions": {
    "can_create_rules": true,
    "can_run_analytics": true,
    "can_generate_reports": true
  }
}
```

**Response 201:**
```json
{ "data": { "id": 11, "email": "newadmin@vpc.com", "invite_sent": true } }
```

---

### POST /users/accept-invite
Accept invite and set password. (Public endpoint, uses invite token)

**Request:**
```json
{
  "invite_token": "tok_abc123",
  "password": "NewSecurePassword123!"
}
```

**Response 200:**
```json
{ "data": { "access_token": "eyJ...", "token_type": "bearer" } }
```

---

### PATCH /users/{user_id}/permissions
Update admin permissions.

**Request:**
```json
{
  "permissions": {
    "can_create_rules": false,
    "can_run_analytics": true,
    "can_generate_reports": true
  }
}
```

---

## 10. Health

### GET /health
Service health check.

**Response 200:**
```json
{
  "status": "healthy",
  "service": "api",
  "version": "1.0.0",
  "dependencies": {
    "mysql": "ok",
    "redis": "ok",
    "influxdb": "ok",
    "minio": "ok"
  }
}
```

---

## Error Codes Reference

| Code | HTTP | Description |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `TOKEN_EXPIRED` | 401 | JWT has expired |
| `INVALID_TOKEN` | 401 | JWT is malformed |
| `FORBIDDEN` | 403 | Insufficient role/permissions |
| `DEVICE_NOT_FOUND` | 404 | Device not found in this factory |
| `RULE_NOT_FOUND` | 404 | Rule not found in this factory |
| `JOB_NOT_FOUND` | 404 | Analytics job not found |
| `DUPLICATE_DEVICE_KEY` | 409 | Device key already exists |
| `DUPLICATE_EMAIL` | 409 | Email already registered |
| `VALIDATION_ERROR` | 422 | Request body invalid |
| `INFLUXDB_UNAVAILABLE` | 503 | Time-series DB unreachable |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

*End of API Specification v1*
