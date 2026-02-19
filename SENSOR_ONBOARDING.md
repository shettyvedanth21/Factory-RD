# SENSOR ONBOARDING GUIDE

**FactoryOps Platform v1.0.0**  
**Last Updated:** February 2026

This document explains how to onboard real IoT devices and sensors to the FactoryOps platform.

---

## Table of Contents

- [PART A: FOR ME (Platform Owner)](#part-a-for-me-platform-owner)
- [PART B: FOR FIRMWARE TEAM (Technical Specification)](#part-b-for-firmware-team-technical-specification)
- [PART C: EMAIL TEMPLATE](#part-c-email-template)

---

# PART A: FOR ME (Platform Owner)

## A1. Pre-Onboarding Checklist

Before onboarding a new factory or device, collect the following information from the firmware team:

### Information Collection Questionnaire

**Send this to the firmware team:**

```
FACTORYOPS DEVICE ONBOARDING QUESTIONNAIRE

Factory Information:
[ ] Factory Name: _________________________________
[ ] Factory Slug (short code, lowercase, no spaces): _________________________________
[ ] Timezone (e.g., Asia/Kolkata, America/New_York): _________________________________

Device Information:
[ ] Number of devices to onboard: _________________________________
[ ] Device types (e.g., compressor, pump, motor): _________________________________
[ ] Device key naming pattern (e.g., M01, M02, PUMP-01): _________________________________

Sensor Parameters:
[ ] List all sensor parameters (e.g., voltage, current, temperature, rpm):
    - _________________________________
    - _________________________________
    - _________________________________
    - _________________________________

[ ] Expected data transmission frequency: _________________________________
[ ] Expected data format: JSON
[ ] MQTT client library they plan to use: _________________________________

Network Information:
[ ] Will devices be on same network as FactoryOps server? Yes / No
[ ] If remote, what is their public IP: _________________________________
[ ] Firewall restrictions: _________________________________

Contact Information:
[ ] Primary firmware engineer name: _________________________________
[ ] Email: _________________________________
[ ] Phone/WhatsApp: _________________________________
```

---

## A2. Register a New Factory

### Step 1: Create Factory via API

**IMPORTANT:** Factory slug must be:
- Lowercase only
- No spaces (use hyphens)
- Alphanumeric + hyphens only
- Between 2-100 characters
- Unique across the platform

**Code validation (from `backend/app/models/factory.py`):**
```python
slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
```

**Command to create factory:**

```bash
curl -X POST http://localhost:8000/api/v1/factories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -d '{
    "name": "ABC Manufacturing Plant",
    "slug": "abc-plant",
    "timezone": "Asia/Kolkata"
  }'
```

**Expected response:**
```json
{
  "data": {
    "id": 2,
    "name": "ABC Manufacturing Plant",
    "slug": "abc-plant",
    "timezone": "Asia/Kolkata",
    "created_at": "2026-02-19T10:30:00Z"
  }
}
```

### Step 2: Verify Factory in Database

```bash
docker compose exec mysql mysql -u factoryops -pfactoryops_dev factoryops \
  -e "SELECT id, name, slug, timezone FROM factories WHERE slug='abc-plant';"
```

**Expected output:**
```
+----+---------------------------+-----------+---------------+
| id | name                      | slug      | timezone      |
+----+---------------------------+-----------+---------------+
|  2 | ABC Manufacturing Plant   | abc-plant | Asia/Kolkata  |
+----+---------------------------+-----------+---------------+
```

### Step 3: Create Super Admin User for Factory

```bash
curl -X POST http://localhost:8000/api/v1/users/invite \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -d '{
    "email": "admin@abcplant.com",
    "role": "super_admin",
    "permissions": {
      "can_create_rules": true,
      "can_run_analytics": true,
      "can_generate_reports": true
    }
  }'
```

---

## A3. How Device Auto-Registration Works

### Automatic Device Discovery

**FactoryOps automatically creates devices when they send their first telemetry message.**

**Code location:** `telemetry/handlers/cache.py` - function `get_or_create_device()`

**Exact implementation (lines 107-181):**
```python
async def get_or_create_device(
    redis: Redis,
    db: AsyncSession,
    factory_id: int,
    device_key: str
) -> Device:
    """
    Get or auto-create device with Redis caching (60-second TTL).
    Enables zero-config device onboarding.
    """
    # Try cache first
    cache_key = f"device:{factory_id}:{device_key}"
    cached = await redis.get(cache_key)
    if cached:
        return device_from_json(cached)
    
    # Query database
    result = await db.execute(
        select(Device).where(
            Device.factory_id == factory_id,
            Device.device_key == device_key
        )
    )
    device = result.scalar_one_or_none()
    
    # Auto-create if not found
    if not device:
        device = Device(
            factory_id=factory_id,
            device_key=device_key,
            name=None,
            is_active=True,
            last_seen=datetime.utcnow()
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        
        logger.info(
            "device.auto_registered",
            factory_id=factory_id,
            device_key=device_key,
            device_id=device.id
        )
    
    # Cache the device
    await redis.setex(cache_key, 60, device_to_json(device))
    return device
```

### What Happens Automatically

1. **First MQTT message arrives** on topic: `factories/abc-plant/devices/M01/telemetry`
2. **Telemetry service parses topic** → extracts `factory_slug="abc-plant"` and `device_key="M01"`
3. **Resolves factory** from slug (using Redis cache + MySQL lookup)
4. **Checks if device exists** for this factory + device_key
5. **If device doesn't exist:**
   - Creates new Device record in MySQL
   - Sets `device_key="M01"`, `name=NULL`, `is_active=True`
   - Assigns auto-incremented `id`
   - Logs: `device.auto_registered` event
6. **Device is now registered** and will appear in UI/API immediately

### What I Will See

**In telemetry service logs:**
```json
{
  "event": "device.auto_registered",
  "factory_id": 2,
  "device_key": "M01",
  "device_id": 15,
  "timestamp": "2026-02-19T10:35:42Z"
}
```

**In API response:**
```bash
curl -X GET http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

```json
{
  "data": [
    {
      "id": 15,
      "factory_id": 2,
      "device_key": "M01",
      "name": null,
      "manufacturer": null,
      "model": null,
      "region": null,
      "is_active": true,
      "last_seen": "2026-02-19T10:35:42Z",
      "created_at": "2026-02-19T10:35:42Z"
    }
  ]
}
```

**In UI:**
- Navigate to **Machines** page
- Device `M01` will appear in the table
- Name will show as "M01" (device_key used as fallback)
- Click device to see detail page

### Verify Device Registration

```bash
# Check MySQL directly
docker compose exec mysql mysql -u factoryops -pfactoryops_dev factoryops \
  -e "SELECT id, factory_id, device_key, name, is_active, last_seen FROM devices ORDER BY id DESC LIMIT 5;"

# Check via API
curl -X GET http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" | jq '.data[] | {id, device_key, last_seen}'
```

---

## A4. Configure KPIs After Device Appears

### Automatic Parameter Discovery

**When device sends telemetry, all metric keys are automatically discovered.**

**Code location:** `telemetry/handlers/parameter_discovery.py` - function `discover_parameters()`

**What happens automatically:**
1. Device sends: `{"metrics": {"voltage": 231.5, "current": 3.2, "power": 745.6}}`
2. Telemetry service extracts keys: `voltage`, `current`, `power`
3. For each new parameter key:
   - Inserts row into `device_parameters` table
   - Sets `data_type` based on value type (float/int/string)
   - Sets `is_kpi_selected=True` by default
   - Logs: `parameter.discovered` event

### Step 1: View Discovered Parameters

```bash
# Via API
curl -X GET http://localhost:8000/api/v1/devices/15/parameters \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "data": [
    {
      "id": 45,
      "device_id": 15,
      "parameter_key": "voltage",
      "display_name": null,
      "unit": null,
      "data_type": "float",
      "is_kpi_selected": true,
      "discovered_at": "2026-02-19T10:35:42Z"
    },
    {
      "id": 46,
      "device_id": 15,
      "parameter_key": "current",
      "display_name": null,
      "unit": null,
      "data_type": "float",
      "is_kpi_selected": true,
      "discovered_at": "2026-02-19T10:35:42Z"
    }
  ]
}
```

### Step 2: Update Parameter Display Names and Units

```bash
curl -X PATCH http://localhost:8000/api/v1/devices/15/parameters/45 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "display_name": "Supply Voltage",
    "unit": "V"
  }'
```

### Step 3: Create Alert Rule

```bash
curl -X POST http://localhost:8000/api/v1/rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "High Voltage Alert",
    "device_ids": [15],
    "condition": {
      "type": "condition",
      "parameter": "voltage",
      "operator": "gt",
      "value": 250
    },
    "severity": "high",
    "cooldown_minutes": 15,
    "notification_channels": ["email"]
  }'
```

### Step 4: Set Up KPI Dashboard (UI Steps)

1. **Navigate to Device Detail Page:**
   - Go to **Machines** → Click **M01**

2. **KPIs are automatically displayed:**
   - All parameters with `is_kpi_selected=True` appear as KPI cards
   - Live values are fetched from InfluxDB (last 5 minutes)
   - Historical charts are generated automatically

3. **Customize KPI Selection:**
   - Click **Configure KPIs** button
   - Toggle parameters on/off
   - Changes save automatically

---

## A5. End-to-End Verification Commands

### 1. Watch MQTT Broker Receive Messages (Live)

```bash
# Subscribe to all telemetry topics
docker compose exec emqx mosquitto_sub -h localhost -p 1883 \
  -t "factories/+/devices/+/telemetry" -v
```

**Expected output (when device publishes):**
```
factories/abc-plant/devices/M01/telemetry {"timestamp":"2026-02-19T10:40:00Z","metrics":{"voltage":231.5,"current":3.2}}
```

### 2. Check Telemetry Service Logs

```bash
docker compose logs -f telemetry | grep "telemetry.processed"
```

**Expected log entry:**
```json
{
  "event": "telemetry.processed",
  "factory_id": 2,
  "device_id": 15,
  "device_key": "M01",
  "metric_count": 2,
  "timestamp": "2026-02-19T10:40:00Z"
}
```

**✅ Success indicator:** Log line appears with `event="telemetry.processed"` and correct `device_id`

### 3. Query InfluxDB Directly

```bash
docker compose exec influxdb influx query \
  'from(bucket:"factoryops")
   |> range(start: -1h)
   |> filter(fn: (r) => r._measurement == "device_metrics")
   |> filter(fn: (r) => r.factory_id == "2")
   |> filter(fn: (r) => r.device_id == "15")
   |> limit(n:10)'
```

**Expected output:**
```
_time                     _measurement    factory_id  device_id  parameter  _value
2026-02-19T10:40:00Z     device_metrics  2           15         voltage    231.5
2026-02-19T10:40:00Z     device_metrics  2           15         current    3.2
```

### 4. Check MySQL for Device + Parameters

```bash
docker compose exec mysql mysql -u factoryops -pfactoryops_dev factoryops -e "
  SELECT d.id, d.device_key, d.last_seen, 
         (SELECT COUNT(*) FROM device_parameters WHERE device_id=d.id) as param_count
  FROM devices d 
  WHERE d.device_key='M01';
"
```

**Expected output:**
```
+----+------------+---------------------+-------------+
| id | device_key | last_seen           | param_count |
+----+------------+---------------------+-------------+
| 15 | M01        | 2026-02-19 10:40:00 |           2 |
+----+------------+---------------------+-------------+
```

### 5. Hit Live KPI Endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/devices/15/kpis/live?parameters=voltage,current" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected response:**
```json
{
  "data": {
    "voltage": {
      "value": 231.5,
      "timestamp": "2026-02-19T10:40:00Z",
      "is_stale": false
    },
    "current": {
      "value": 3.2,
      "timestamp": "2026-02-19T10:40:00Z",
      "is_stale": false
    }
  }
}
```

**✅ Success indicators:**
- `is_stale: false` (data received in last 5 minutes)
- `value` matches what device published
- `timestamp` is recent

### 6. Verify Parameter Discovery

```bash
docker compose exec mysql mysql -u factoryops -pfactoryops_dev factoryops -e "
  SELECT parameter_key, data_type, is_kpi_selected, discovered_at 
  FROM device_parameters 
  WHERE device_id=15;
"
```

**Expected output:**
```
+---------------+-----------+-----------------+---------------------+
| parameter_key | data_type | is_kpi_selected | discovered_at       |
+---------------+-----------+-----------------+---------------------+
| voltage       | float     |               1 | 2026-02-19 10:35:42 |
| current       | float     |               1 | 2026-02-19 10:35:42 |
+---------------+-----------+-----------------+---------------------+
```

---

## A6. My Troubleshooting Guide

| Symptom | What to Check | Exact Command | Fix |
|---------|--------------|---------------|-----|
| **Device not appearing in UI** | 1. MQTT message received? | `docker compose logs telemetry | grep "device_key"` | Check topic format matches `factories/{slug}/devices/{key}/telemetry` |
| | 2. Factory exists? | `docker compose exec mysql mysql -u factoryops -pfactoryops_dev factoryops -e "SELECT * FROM factories WHERE slug='abc-plant';"` | Create factory first via API |
| | 3. Telemetry service running? | `docker compose ps telemetry` | `docker compose restart telemetry` |
| | 4. Any errors in logs? | `docker compose logs telemetry | grep ERROR` | Check payload format (must be valid JSON) |
| **Data in InfluxDB but not showing in API** | 1. InfluxDB query working? | `curl http://localhost:8086/health` | Restart InfluxDB if down |
| | 2. Factory_id tag correct? | Query InfluxDB directly (see A5.3) | Device might be sending to wrong factory topic |
| | 3. API can reach InfluxDB? | Check backend logs for InfluxDB connection errors | Check `INFLUXDB_URL` in .env |
| **Parameters not auto-discovered** | 1. Metrics in payload? | `docker compose logs telemetry | grep "telemetry.processed" | jq .metric_count` | Must be non-empty `metrics` object |
| | 2. Parameter discovery logged? | `docker compose logs telemetry | grep "parameter.discovered"` | Check metrics are numeric (not strings) |
| | 3. Database write successful? | `docker compose logs telemetry | grep ERROR` | Check MySQL connection |
| **is_stale showing true** | 1. Last message timestamp | `docker compose exec mysql mysql -u factoryops -pfactoryops_dev factoryops -e "SELECT device_key, last_seen FROM devices WHERE id=15;"` | Device hasn't sent data in >5 minutes |
| | 2. MQTT connection active? | `docker compose exec emqx emqx_ctl clients show` | Device disconnected from broker |
| **MQTT not connecting** | 1. Broker running? | `docker compose ps emqx` | `docker compose restart emqx` |
| | 2. Port exposed? | `netstat -an | grep 1883` | Check firewall or docker-compose port mapping |
| | 3. Credentials required? | Check `.env` for `MQTT_USERNAME` and `MQTT_PASSWORD` | If set, device must authenticate |
| **Duplicate devices created** | 1. Device_key case-sensitive? | `docker compose exec mysql mysql -u factoryops -pfactoryops_dev factoryops -e "SELECT device_key FROM devices WHERE factory_id=2;"` | Use consistent casing (case-sensitive!) |
| **Rule not triggering** | 1. Rule active? | `curl http://localhost:8000/api/v1/rules -H "Authorization: Bearer TOKEN"` | Check `is_active=true` |
| | 2. Device ID matches? | Check `device_ids` array in rule | Must include device's database ID, not key |
| | 3. Celery worker running? | `docker compose ps worker` | `docker compose restart worker` |
| | 4. Rule evaluation logs? | `docker compose logs worker | grep "rule_engine"` | Check for evaluation errors |

---

# PART B: FOR FIRMWARE TEAM (Technical Specification)

## B1. Plain English Summary

**What you need to do:**
1. Connect to our MQTT broker using the credentials we provide
2. Publish sensor readings as JSON messages to a specific topic format
3. Send data at regular intervals (recommended: every 5-30 seconds depending on sensor type)

**What you do NOT need to do:**
- Register devices beforehand (auto-registration happens on first message)
- Create database schemas (parameters are discovered automatically)
- Handle authentication beyond MQTT credentials
- Parse or validate responses (fire-and-forget publishing)

---

## B2. MQTT Connection Details

**Connection configuration values (from `docker/docker-compose.yml` and `.env.example`):**

| Parameter | Development Value | Production Value | Notes |
|-----------|------------------|------------------|-------|
| **Broker Host** | `localhost` or `<SERVER_IP>` | Will be provided separately | Use server's public IP or domain |
| **Port** | `1883` | `1883` | Standard MQTT port (non-TLS) |
| **Username** | `""` (empty) | Will be provided if needed | Optional, check with platform team |
| **Password** | `""` (empty) | Will be provided if needed | Optional, check with platform team |
| **Protocol** | MQTT v3.1.1 or v5.0 | MQTT v3.1.1 or v5.0 | Both supported |
| **QoS** | `1` (recommended) | `1` (recommended) | At-least-once delivery |
| **Keep-Alive** | `60` seconds | `60` seconds | Send ping every 60s |
| **Clean Session** | `true` | `true` | Don't persist session state |
| **Client ID** | Any unique string | Device serial number recommended | Must be unique per device |

**MQTT Broker Implementation:** EMQX (from `docker/docker-compose.yml`, service `emqx`)

---

## B3. Topic Format — CRITICAL

### Exact Topic String

**Format (from `telemetry/schemas.py`, function `parse_topic()`):**

```
factories/{factory_slug}/devices/{device_key}/telemetry
```

### Topic Parsing Logic (Actual Code)

```python
def parse_topic(topic: str) -> tuple[str, str]:
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
```

### Variable Definitions

| Variable | Definition | Who Provides | Character Rules | Example |
|----------|-----------|--------------|-----------------|---------|
| `{factory_slug}` | Unique factory identifier | **Platform team** | Lowercase, alphanumeric + hyphens, 2-100 chars | `vpc`, `abc-plant`, `factory-01` |
| `{device_key}` | Unique device identifier within factory | **You (firmware team)** | Alphanumeric, max 100 chars, **case-sensitive** | `M01`, `PUMP-01`, `COMPRESSOR-A1` |

### Valid Topic Examples

✅ **CORRECT:**
1. `factories/vpc/devices/M01/telemetry`
2. `factories/abc-plant/devices/PUMP-01/telemetry`
3. `factories/factory-01/devices/SENSOR-TEMP-001/telemetry`
4. `factories/demo/devices/ABC123/telemetry`
5. `factories/my-factory/devices/device_001/telemetry`

### Invalid Topic Examples

❌ **WRONG:**
1. `factory/vpc/devices/M01/telemetry` ❌ Missing "ies" in "factories"
2. `factories/vpc/device/M01/telemetry` ❌ Missing "s" in "devices"  
3. `factories/vpc/devices/M01/data` ❌ Must end with "telemetry", not "data"
4. `factories/VPC/devices/M01/telemetry` ❌ Factory slug must be lowercase (case-sensitive!)
5. `factories/vpc/devices/M01` ❌ Missing "/telemetry" at the end
6. `vpc/devices/M01/telemetry` ❌ Missing "factories/" prefix
7. `factories/vpc/M01/telemetry` ❌ Missing "devices/" segment
8. `factories/vpc/devices/M 01/telemetry` ❌ Space in device_key (use hyphen or underscore)

---

## B4. JSON Payload — Exact Schema

### Payload Schema (from `telemetry/schemas.py`)

```python
class TelemetryPayload(BaseModel):
    timestamp: Optional[datetime] = None
    metrics: Dict[str, Union[float, int]]
```

### Field-by-Field Rules

| Field | Type | Required | Rules | Default if Omitted |
|-------|------|----------|-------|-------------------|
| `timestamp` | ISO 8601 string | **No** | UTC timezone, format: `YYYY-MM-DDTHH:MM:SSZ` | Server timestamp (UTC) |
| `metrics` | Object (dict) | **Yes** | Keys: alphanumeric strings, Values: numbers only | N/A (required) |

### Timestamp Format Rules

**Format:** ISO 8601 with UTC timezone

**✅ Valid timestamp formats:**
- `"2026-02-19T10:40:00Z"` (recommended)
- `"2026-02-19T10:40:00.123Z"` (with milliseconds)
- `"2026-02-19T10:40:00+00:00"` (explicit UTC offset)

**❌ Invalid timestamp formats:**
- `"2026-02-19 10:40:00"` ❌ Missing T separator and Z suffix
- `"2026-02-19T10:40:00"` ❌ Missing timezone (ambiguous)
- `"2026-02-19T15:10:00+05:30"` ❌ Local timezone (use UTC only)
- `"1708340400"` ❌ Unix timestamp (use ISO 8601)

**What happens if you omit timestamp:**
- Server uses `datetime.utcnow()` (server's current UTC time)
- **Risk:** Clock skew if device and server are out of sync
- **Recommendation:** Always include timestamp from device's RTC (synced via NTP)

### Metrics Object Rules

**Key Rules (parameter names):**
- Must be strings
- Alphanumeric + underscores recommended (e.g., `power_factor`, `temp_celsius`)
- **Case-sensitive** (`Voltage` ≠ `voltage`)
- Max 100 characters (from database column: `parameter_key VARCHAR(100)`)
- Do NOT include units in key name (e.g., use `temperature`, not `temperature_celsius`)

**Value Rules:**
- Must be **numeric** (int or float)
- Strings, booleans, nulls, arrays, or objects are **rejected**
- NaN, Infinity, or null values will cause validation error

**Validation Code (from `telemetry/schemas.py`):**
```python
@model_validator(mode='after')
def validate_metrics(self):
    if not self.metrics:
        raise ValueError("metrics cannot be empty")
    
    for key, value in self.metrics.items():
        if not isinstance(value, (int, float)):
            raise ValueError(f"metric '{key}' must be numeric, got {type(value).__name__}")
    
    return self
```

### Complete Payload Examples

#### Example 1: Power Meter (Recommended Full Payload)

```json
{
  "timestamp": "2026-02-19T10:40:00Z",
  "metrics": {
    "voltage": 231.5,
    "current": 3.2,
    "power": 745.6,
    "frequency": 50.01,
    "power_factor": 0.98
  }
}
```

#### Example 2: Temperature and Pressure Sensor

```json
{
  "timestamp": "2026-02-19T10:40:15Z",
  "metrics": {
    "temperature": 45.5,
    "pressure": 101.3,
    "humidity": 65.2
  }
}
```

#### Example 3: Motor/Pump (with vibration axes)

```json
{
  "timestamp": "2026-02-19T10:40:30Z",
  "metrics": {
    "rpm": 1500,
    "torque": 85.3,
    "vibration_x": 0.15,
    "vibration_y": 0.12,
    "vibration_z": 0.08,
    "bearing_temp": 62.5
  }
}
```

#### Example 4: Minimal Single-Metric Payload

```json
{
  "metrics": {
    "temperature": 23.5
  }
}
```

**Note:** Timestamp omitted → server will use current UTC time

---

## B5. Sending Frequency

### Recommended Intervals by Sensor Type

| Sensor Type | Recommended Interval | Reason |
|-------------|---------------------|--------|
| **Power meters** | 5-10 seconds | Energy consumption calculations need frequent samples |
| **Temperature sensors** | 30-60 seconds | Temperature changes slowly |
| **Vibration sensors** | 1-5 seconds | Detect anomalies quickly |
| **Pressure sensors** | 10-30 seconds | Balance between data granularity and bandwidth |
| **Flow meters** | 10-30 seconds | Similar to pressure |
| **RPM/Speed sensors** | 5-10 seconds | Detect changes in machine operation |
| **Door/Contact sensors** | On change (event-driven) | No need for periodic updates |

### One Message Per Publish Rule

⚠️ **IMPORTANT:** Publish one JSON payload per MQTT message.

**✅ Correct approach:**
```python
# Publish each reading separately
client.publish("factories/vpc/devices/M01/telemetry", 
               '{"metrics":{"voltage":231.5}}')
await asyncio.sleep(5)
client.publish("factories/vpc/devices/M01/telemetry", 
               '{"metrics":{"voltage":232.1}}')
```

**❌ Wrong approach (DO NOT batch into array):**
```json
[
  {"timestamp": "2026-02-19T10:40:00Z", "metrics": {"voltage": 231.5}},
  {"timestamp": "2026-02-19T10:40:05Z", "metrics": {"voltage": 232.1}}
]
```
**Why this fails:** Schema expects a single object, not an array.

### Rate Limiting

**Current implementation:** No rate limiting enforced

**However:**
- InfluxDB may struggle with >100 messages/second per device
- Recommended max: 1 message per second per device
- If you need higher frequency, contact platform team to discuss batching strategy

---

## B6. Device Key Naming Convention

| Machine Type | Key Format | Example | Notes |
|--------------|-----------|---------|-------|
| **Compressors** | `COMP-{number}` | `COMP-01`, `COMP-02` | Zero-padded 2-digit number |
| **Pumps** | `PUMP-{number}` | `PUMP-01`, `PUMP-15` | Zero-padded 2-digit number |
| **Motors** | `MOTOR-{zone}-{number}` | `MOTOR-A-01`, `MOTOR-B-03` | Include zone identifier |
| **Sensors (standalone)** | `SENSOR-{type}-{number}` | `SENSOR-TEMP-01`, `SENSOR-PRESS-05` | Include sensor type |
| **Production Lines** | `LINE-{number}` | `LINE-01`, `LINE-02` | For integrated line controllers |
| **Generic/Other** | `{SERIAL}` | `ABC123456`, `DEV-001` | Use device serial number or custom ID |

### Critical Warning

⚠️ **NEVER change a device_key after data starts flowing!**

**Why:**
- Device_key is the primary identifier for linking telemetry to devices
- Changing it creates a new device record in the database
- Historical data will be orphaned under the old key
- Dashboards and alerts will break

**If you must change:**
1. Export all historical data for the old device_key
2. Contact platform team to migrate data
3. Update firmware with new device_key
4. Verify migration before decommissioning old key

---

## B7. What Happens Automatically

When your device publishes its first message to the platform, the following happens **automatically** without any manual intervention:

✅ **Device Auto-Registration:**
- Device record created in database
- Assigned unique database ID
- Appears immediately in UI (Machines page)
- Status set to "Active"

✅ **Parameter Discovery:**
- All metric keys extracted from `metrics` object
- Each parameter registered in `device_parameters` table
- Data type inferred (float/int)
- All parameters enabled for KPI dashboard by default
- Parameters appear in Device Detail page

✅ **Time-Series Data Storage:**
- Every metric written to InfluxDB with tags: `factory_id`, `device_id`, `parameter`
- Retained for 90 days by default
- Queryable immediately via KPI API endpoints

✅ **Dashboard Availability:**
- Live KPI cards render on Device Detail page
- Historical charts generated automatically
- Data refreshes every 5 seconds

✅ **Health Monitoring:**
- `last_seen` timestamp updated on every message
- Device status calculated based on last_seen (online if < 10 min)
- Health score contributes to factory-wide health metric

**What is NOT automatic (requires platform team configuration):**
- Alert rules (need to be created via API/UI)
- Custom KPI thresholds (defaults to showing raw values)
- Notification channels (email/WhatsApp need SMTP/Twilio configuration)
- Parameter display names and units (default to raw key names)

---

## B8. Test Script — Python

### Installation

```bash
pip install paho-mqtt
```

### Complete Working Script

Save as `test_mqtt_connection.py`:

```python
#!/usr/bin/env python3
"""
FactoryOps MQTT Test Script
Publishes test telemetry data to verify connection.
"""
import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# ===== CONFIGURATION (UPDATE THESE VALUES) =====
BROKER_HOST = "localhost"  # Change to server IP or domain
BROKER_PORT = 1883
MQTT_USERNAME = ""  # Leave empty if not required
MQTT_PASSWORD = ""  # Leave empty if not required

FACTORY_SLUG = "vpc"  # Get from platform team
DEVICE_KEY = "TEST-001"  # Choose your device key

# ===== MQTT CALLBACKS =====
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker successfully!")
        print(f"   Broker: {BROKER_HOST}:{BROKER_PORT}")
    else:
        print(f"❌ Connection failed with code {rc}")
        print("   Error codes:")
        print("   1 = Incorrect protocol version")
        print("   2 = Invalid client identifier")
        print("   3 = Server unavailable")
        print("   4 = Bad username or password")
        print("   5 = Not authorized")

def on_publish(client, userdata, mid):
    print(f"✅ Message published successfully (ID: {mid})")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"⚠️  Unexpected disconnection (code {rc})")

# ===== MAIN SCRIPT =====
def main():
    # Create MQTT client
    client = mqtt.Client(client_id=f"{DEVICE_KEY}-test")
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    
    # Set credentials if provided
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        print(f"🔐 Using authentication: {MQTT_USERNAME}")
    
    # Connect to broker
    print(f"🔌 Connecting to {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    # Start network loop
    client.loop_start()
    
    # Wait for connection
    time.sleep(2)
    
    # Build topic
    topic = f"factories/{FACTORY_SLUG}/devices/{DEVICE_KEY}/telemetry"
    print(f"📡 Publishing to topic: {topic}")
    
    # Publish 5 test messages
    for i in range(1, 6):
        # Build payload
        payload = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "metrics": {
                "voltage": 230.0 + i,
                "current": 3.0 + (i * 0.1),
                "power": 750.0 + (i * 10),
                "temperature": 25.0 + (i * 0.5)
            }
        }
        
        # Convert to JSON
        payload_json = json.dumps(payload)
        
        # Publish with QoS 1
        result = client.publish(topic, payload_json, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"📤 Message {i}/5 sent:")
            print(f"   {payload_json}")
        else:
            print(f"❌ Publish failed with code {result.rc}")
        
        # Wait before next message
        time.sleep(2)
    
    # Wait for all messages to be sent
    time.sleep(2)
    
    # Disconnect
    client.loop_stop()
    client.disconnect()
    
    print("\n✅ Test complete!")
    print("\nNext steps:")
    print("1. Check telemetry service logs for 'telemetry.processed' events")
    print("2. Verify device appeared in UI: http://<server>/machines")
    print("3. Check parameters were discovered: http://<server>/machines/<device>")

if __name__ == "__main__":
    main()
```

### Running the Script

```bash
# 1. Update configuration variables in the script
# 2. Run the script
python3 test_mqtt_connection.py
```

### Expected Output

```
🔌 Connecting to localhost:1883...
✅ Connected to MQTT broker successfully!
   Broker: localhost:1883
📡 Publishing to topic: factories/vpc/devices/TEST-001/telemetry
📤 Message 1/5 sent:
   {"timestamp":"2026-02-19T10:45:00Z","metrics":{"voltage":231.0,"current":3.1,"power":760.0,"temperature":25.5}}
✅ Message published successfully (ID: 1)
📤 Message 2/5 sent:
   {"timestamp":"2026-02-19T10:45:02Z","metrics":{"voltage":232.0,"current":3.2,"power":770.0,"temperature":26.0}}
✅ Message published successfully (ID: 2)
...
✅ Test complete!
```

---

## B9. Common Mistakes Table

| ❌ Wrong | ✅ Correct | Why It Fails |
|----------|-----------|--------------|
| Topic: `Factory/vpc/devices/M01/telemetry` | `factories/vpc/devices/M01/telemetry` | First word must be lowercase "factories" (case-sensitive) |
| Topic: `factories/VPC/devices/M01/telemetry` | `factories/vpc/devices/M01/telemetry` | Factory slug is case-sensitive and stored lowercase in database |
| Payload: `{"voltage": 231.5}` | `{"metrics": {"voltage": 231.5}}` | Must have `metrics` wrapper object |
| Metrics: `{"voltage": "231.5"}` | `{"voltage": 231.5}` | Values must be numbers, not strings |
| Metrics: `{"temp_celsius": 45.5}` | `{"temperature": 45.5}` | Don't include units in parameter names (configure units in UI later) |
| Timestamp: `"2026-02-19 10:40:00"` | `"2026-02-19T10:40:00Z"` | Must use ISO 8601 format with T separator and Z timezone |
| Timestamp: `"2026-02-19T15:10:00+05:30"` | `"2026-02-19T09:40:00Z"` | Always use UTC (Z suffix), not local timezone offsets |
| Batching: `[{...}, {...}]` | Publish each message separately | Payload must be a single object, not an array |
| Empty metrics: `{"metrics": {}}` | `{"metrics": {"voltage": 231.5}}` | Metrics object cannot be empty (validation error) |
| Device key: `M 01` | `M01` or `M-01` | No spaces allowed in device keys (use hyphens or underscores) |
| Special chars: `{"temp°C": 45.5}` | `{"temp_celsius": 45.5}` | Avoid special characters in parameter keys (use alphanumeric + underscores) |
| Changing device_key mid-operation | Never change device_key | Creates new device in DB, orphans historical data |

---

## B10. Checklist of What You Need From Platform Team

Before you can start sending data, the platform team must provide:

**Connection Details:**
- [ ] MQTT broker IP address or hostname
- [ ] MQTT port number (confirm if standard 1883 or custom)
- [ ] MQTT username (if authentication enabled)
- [ ] MQTT password (if authentication enabled)
- [ ] Factory slug (your unique factory identifier)

**Network Information:**
- [ ] Is the broker accessible from your network? (firewall rules)
- [ ] VPN required? If yes, VPN configuration details
- [ ] Static IP or dynamic DNS for broker?

**Configuration Guidance:**
- [ ] Recommended data transmission interval for your sensor type
- [ ] Device key naming convention for your devices
- [ ] List of required parameters (metric names) if standardized
- [ ] Alert thresholds (if you want rules pre-configured)

**Verification Support:**
- [ ] Access to telemetry service logs (or instructions to check)
- [ ] Test credentials for UI access (to verify device appears)
- [ ] Contact person for troubleshooting

**Optional (for advanced features):**
- [ ] Email addresses for alert notifications
- [ ] WhatsApp numbers for critical alerts
- [ ] KPI threshold values
- [ ] Custom dashboard configuration

---

# PART C: EMAIL TEMPLATE

## Professional Onboarding Email

**Subject:** FactoryOps IoT Platform - Device Onboarding Instructions for [FACTORY_NAME]

---

**To:** [FIRMWARE_ENGINEER_EMAIL]  
**From:** [YOUR_EMAIL]  
**Date:** [CURRENT_DATE]

---

Dear [FIRMWARE_ENGINEER_NAME],

I hope this email finds you well.

We're excited to onboard [FACTORY_NAME] to the **FactoryOps AI Engineering Platform** — an industrial IoT platform that provides real-time monitoring, predictive analytics, and intelligent alerting for your manufacturing equipment.

### What We Need You to Implement

Your devices need to send sensor data to our MQTT broker using a simple JSON format. Here's what's required:

**1. MQTT Connection**

Connect your devices to our broker with these details:

```
Host: [BROKER_IP_OR_HOSTNAME]
Port: 1883
Username: [MQTT_USERNAME] (leave blank if not provided)
Password: [MQTT_PASSWORD] (leave blank if not provided)
QoS: 1 (recommended)
Keep-Alive: 60 seconds
```

**2. Topic Format**

Publish telemetry data to this exact topic structure:

```
factories/[FACTORY_SLUG]/devices/{device_key}/telemetry
```

Replace:
- `[FACTORY_SLUG]` = **[FACTORY_SLUG]** (your factory identifier — use exactly this value)
- `{device_key}` = Your device's unique identifier (e.g., `M01`, `PUMP-01`, `SENSOR-TEMP-001`)

**Example topics for your devices:**
- `factories/[FACTORY_SLUG]/devices/M01/telemetry`
- `factories/[FACTORY_SLUG]/devices/M02/telemetry`
- `factories/[FACTORY_SLUG]/devices/PUMP-01/telemetry`

⚠️ **Important:** Topic is case-sensitive. Use the factory slug exactly as provided.

**3. JSON Payload Format**

Send sensor readings in this JSON structure:

```json
{
  "timestamp": "2026-02-19T10:40:00Z",
  "metrics": {
    "voltage": 231.5,
    "current": 3.2,
    "power": 745.6,
    "temperature": 45.5
  }
}
```

**Field rules:**
- `timestamp` (optional): ISO 8601 format in UTC (e.g., `2026-02-19T10:40:00Z`)
- `metrics` (required): Object containing your sensor parameters
  - Keys: Parameter names (lowercase, use underscores, no units)
  - Values: Numeric only (integers or floats)

**4. Recommended Parameters for Your Equipment**

Based on your [EQUIPMENT_TYPE], we recommend sending these parameters:

[CUSTOMIZE THIS LIST BASED ON EQUIPMENT TYPE]

For **power meters / electrical equipment:**
- voltage, current, power, frequency, power_factor

For **motors / pumps:**
- rpm, torque, vibration_x, vibration_y, vibration_z, bearing_temp

For **temperature/pressure sensors:**
- temperature, pressure, humidity

For **flow meters:**
- flow_rate, totalizer, pressure

**5. Sending Frequency**

Recommended transmission interval: **[RECOMMENDED_INTERVAL]** seconds

Adjust based on your sensor type:
- Critical equipment (power, vibration): 5-10 seconds
- Temperature/pressure: 30-60 seconds
- Flow/level sensors: 10-30 seconds

**6. Test Script**

Attached is a Python test script (`test_mqtt_connection.py`) you can use to verify connectivity before implementing in your firmware. Update the configuration variables at the top of the script with the values provided above.

```bash
# Install dependencies
pip install paho-mqtt

# Update configuration in script, then run
python3 test_mqtt_connection.py
```

### What Happens Automatically

Once your devices start sending data:

✅ **Devices auto-register** — No manual device creation needed  
✅ **Parameters auto-discovered** — All metric keys automatically registered  
✅ **Dashboards available immediately** — Real-time KPI cards and charts  
✅ **Historical data stored** — Retained for 90 days by default  

You'll be able to see your devices in the web dashboard at: **[DASHBOARD_URL]**

### What to Report Back

After implementing and testing, please confirm:

1. ✅ Successfully connected to MQTT broker
2. ✅ Messages publishing without errors
3. ✅ Devices appearing in FactoryOps web dashboard
4. ✅ Live data visible on device detail pages

**Verification steps:**
- Check if your devices appear at: [DASHBOARD_URL]/machines
- Click on a device to see live KPI values
- Confirm timestamp is recent (< 5 minutes)

### Important Notes

⚠️ **Device Key Consistency:** Once you choose a device_key (e.g., `M01`), never change it. The system uses this as the primary identifier.

⚠️ **Case Sensitivity:** Topic format is case-sensitive. Factory slug must be exactly: **[FACTORY_SLUG]**

⚠️ **Numeric Values Only:** All metric values must be numbers, not strings.

⚠️ **UTC Timestamps:** Always use UTC timezone (Z suffix), not local time.

### Network & Firewall

**Outbound connection required:**
- Protocol: TCP
- Destination: [BROKER_IP_OR_HOSTNAME]
- Port: 1883

If your devices are behind a firewall, please ensure this outbound connection is allowed.

### Support & Questions

I'm here to help! If you encounter any issues or have questions:

📧 Email: [YOUR_EMAIL]  
📱 Phone/WhatsApp: [YOUR_PHONE]  
⏰ Available: [YOUR_AVAILABILITY]

We can also schedule a call to walk through the integration together.

### Additional Resources

I've attached the complete **SENSOR_ONBOARDING.md** document which includes:
- Detailed troubleshooting guide
- Common mistakes to avoid
- Complete Python test script
- End-to-end verification commands

### Timeline

We'd like to have devices sending test data by: **[TARGET_DATE]**

Please let me know if this timeline works for you, or if you need any adjustments.

Looking forward to getting your equipment connected to the platform!

Best regards,

[YOUR_NAME]  
[YOUR_TITLE]  
[COMPANY_NAME]  
[YOUR_EMAIL]  
[YOUR_PHONE]

---

**Attachments:**
- SENSOR_ONBOARDING.md (complete technical guide)
- test_mqtt_connection.py (Python test script)

---

## Quick Copy-Paste Values

**For your convenience, here are the exact values to use:**

```
MQTT Broker: [BROKER_IP_OR_HOSTNAME]
MQTT Port: 1883
MQTT Username: [MQTT_USERNAME]
MQTT Password: [MQTT_PASSWORD]
Factory Slug: [FACTORY_SLUG]

Example Topic: factories/[FACTORY_SLUG]/devices/M01/telemetry

Example Payload:
{
  "timestamp": "2026-02-19T10:40:00Z",
  "metrics": {
    "voltage": 231.5,
    "current": 3.2,
    "power": 745.6,
    "temperature": 45.5
  }
}
```

---

## Test Script Configuration

**Update these lines in `test_mqtt_connection.py`:**

```python
BROKER_HOST = "[BROKER_IP_OR_HOSTNAME]"
BROKER_PORT = 1883
MQTT_USERNAME = "[MQTT_USERNAME]"  # Or "" if not required
MQTT_PASSWORD = "[MQTT_PASSWORD]"  # Or "" if not required
FACTORY_SLUG = "[FACTORY_SLUG]"
DEVICE_KEY = "TEST-001"  # Change to your device's key
```

---

