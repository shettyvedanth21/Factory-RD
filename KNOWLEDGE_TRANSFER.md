# FactoryOps Knowledge Transfer Document

**Version:** 1.0.0  
**Last Updated:** February 2026  
**Target Audience:** New developers with zero prior knowledge of the project

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Data Architecture](#3-data-architecture)
4. [Complete Data Flows](#4-complete-data-flows)
5. [API Reference](#5-api-reference)
6. [Multi-Tenancy & Security](#6-multi-tenancy--security)
7. [Frontend Structure](#7-frontend-structure)
8. [How To Run & Debug](#8-how-to-run--debug)
9. [How To Extend](#9-how-to-extend)
10. [Deployment](#10-deployment)

---

## 1. Project Overview

### 1.1 What Problem Does This Solve?

FactoryOps is an **Industrial IoT Platform** designed to monitor, analyze, and optimize factory operations in real-time. It solves the following problems:

1. **Real-Time Equipment Monitoring**: Track voltage, current, power, temperature, pressure, and other parameters from industrial machines via MQTT telemetry
2. **Predictive Maintenance**: Use AI to detect anomalies and predict equipment failures before they occur
3. **Rule-Based Alerting**: Automatically trigger alerts when equipment operates outside safe parameters
4. **Energy Optimization**: Monitor and analyze energy consumption patterns across all devices
5. **Multi-Factory Management**: Support multiple factories with complete data isolation
6. **Automated Reporting**: Generate PDF/Excel reports with telemetry summaries and analytics results

### 1.2 Who Uses It and How?

**Primary Users:**
- **Factory Managers**: Monitor overall factory health, energy consumption, and alert trends via dashboard
- **Operations Engineers**: Create alerting rules, investigate equipment issues, review KPI trends
- **Maintenance Teams**: Respond to alerts, view device health scores, track maintenance patterns
- **Data Analysts**: Run analytics jobs (anomaly detection, forecasting), generate reports

**User Journey:**
1. User logs in → Selects their factory → Dashboard loads with real-time metrics
2. Navigates to "Machines" → Views all devices with health scores and active alerts
3. Clicks a device → Sees live KPI values and historical charts
4. Creates alert rules → Gets notified via email/WhatsApp when conditions trigger
5. Runs analytics → Reviews anomaly detection or energy forecast results
6. Generates reports → Downloads PDF/Excel with telemetry summary

### 1.3 Key Business Concepts

#### **Factory**
- **Definition**: A physical manufacturing site (e.g., "VPC Factory")
- **Purpose**: Top-level tenant isolation boundary
- **Attributes**: Name, slug (URL-safe identifier), timezone
- **Example**: Factory "VPC" with slug `vpc` owns devices M01, M02, etc.

#### **Device**
- **Definition**: An industrial machine or sensor (e.g., "Compressor 1", "Pump 3")
- **Purpose**: Source of telemetry data
- **Attributes**: device_key (unique per factory), name, manufacturer, model, region, is_active, last_seen
- **Example**: Device with key `M01` publishes to MQTT topic `factories/vpc/devices/M01/telemetry`

#### **Parameter**
- **Definition**: A specific metric/sensor reading (e.g., "voltage", "temperature")
- **Purpose**: Individual time-series data stream from a device
- **Attributes**: parameter_key, display_name, unit, data_type (float/int/string), is_kpi_selected
- **Example**: Parameter `voltage` with unit "V" and data_type "float"

#### **KPI (Key Performance Indicator)**
- **Definition**: A selected parameter displayed prominently on dashboards
- **Purpose**: Quick visual monitoring of critical metrics
- **Attributes**: Live value, timestamp, is_stale flag (>10min old)
- **Example**: Live voltage = 231.4V (updated 2 seconds ago)

#### **Alert**
- **Definition**: An event triggered when a rule condition is met
- **Purpose**: Notify operators of abnormal conditions
- **Attributes**: severity (low/medium/high/critical), message, triggered_at, resolved_at, telemetry_snapshot
- **Example**: "High Voltage Alert: voltage (245.2) > 240" with severity CRITICAL

#### **Rule**
- **Definition**: A condition tree that triggers alerts when telemetry matches
- **Purpose**: Automated equipment monitoring
- **Attributes**: conditions (nested AND/OR logic), severity, cooldown_minutes, schedule, notification_channels
- **Example**: Rule "Overvoltage" triggers when `voltage > 240 OR current > 15` with 15-minute cooldown

#### **Analytics Job**
- **Definition**: A background task that runs ML analysis on historical data
- **Purpose**: Predictive insights (anomaly detection, failure prediction, forecasting)
- **Attributes**: job_type (anomaly/forecast/ai_copilot), device_ids, date_range, status (pending/running/complete/failed)
- **Example**: Anomaly detection job analyzing 7 days of voltage data across 3 devices

#### **Report**
- **Definition**: A generated document summarizing telemetry and alerts
- **Purpose**: Periodic performance reviews, compliance documentation
- **Attributes**: format (PDF/Excel/JSON), device_ids, date_range, include_analytics flag
- **Example**: Monthly PDF report with device stats, alert log, and energy forecast

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React + TypeScript)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Dashboard │  │ Machines │  │  Rules   │  │Analytics │  │ Reports  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │             │             │             │             │        │
│       └─────────────┴─────────────┴─────────────┴─────────────┘        │
│                                   │                                     │
└───────────────────────────────────┼─────────────────────────────────────┘
                                    │ HTTP/REST (JWT Auth)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      NGINX (Reverse Proxy + TLS)                        │
│                         Port 80/443 → Port 8000                         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  API SERVICE (FastAPI + Python 3.11)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Auth    │  │ Devices  │  │  Rules   │  │Analytics │  │ Reports  │ │
│  │Dashboard │  │  KPIs    │  │ Alerts   │  │ Telemetry│  │  Users   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │             │             │             │             │        │
└───────┼─────────────┼─────────────┼─────────────┼─────────────┼────────┘
        │             │             │             │             │
        ▼             ▼             ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐
│   MySQL     │ │  InfluxDB   │ │   Redis     │ │   MinIO     │ │ Celery │
│(Metadata DB)│ │(Time-Series)│ │(Cache+Queue)│ │(File Store) │ │Workers │
│             │ │             │ │             │ │             │ │        │
│ • Factories │ │ • Telemetry │ │ • Sessions  │ │ • Reports   │ │ • Rules│
│ • Users     │ │ • Metrics   │ │ • Device    │ │ • Analytics │ │ • Notif│
│ • Devices   │ │   (voltage, │ │   Cache     │ │   Results   │ │ • Analy│
│ • Rules     │ │   current,  │ │ • Celery    │ │             │ │ • Report│
│ • Alerts    │ │   power,...)│ │   Broker    │ │             │ │        │
│ • Jobs      │ │             │ │             │ │             │ │        │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └────────┘
        ▲             ▲             ▲             
        │             │             │             
        └─────────────┴─────────────┘             
                      │                           
                      ▼                           
┌─────────────────────────────────────────────────────────────────────────┐
│              TELEMETRY SERVICE (Python 3.11 + MQTT)                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ MQTT Subscriber Loop (Never Crashes)                              │ │
│  │ • Subscribes to: factories/+/devices/+/telemetry                  │ │
│  │ • Handles all exceptions internally                               │ │
│  └───┬────────────────────────────────────────────────────────────────┘ │
│      │                                                                  │
│      ▼                                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Ingestion Pipeline (process_telemetry function)                   │ │
│  │ 1. Parse topic → extract factory_slug, device_key                 │ │
│  │ 2. Validate JSON payload → Pydantic schema                        │ │
│  │ 3. Resolve factory (Redis cache → MySQL fallback)                 │ │
│  │ 4. Get/create device (Redis cache → MySQL fallback)               │ │
│  │ 5. Discover new parameters (idempotent MySQL upsert)              │ │
│  │ 6. Write to InfluxDB (batch writes)                               │ │
│  │ 7. Update device.last_seen timestamp                              │ │
│  │ 8. Dispatch rule evaluation to Celery (non-blocking)              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                      ▲
                      │ MQTT Protocol (Port 1883)
                      │
┌─────────────────────────────────────────────────────────────────────────┐
│                     EMQX (MQTT Broker)                                  │
│  • Receives telemetry from IoT devices                                 │
│  • Topic pattern: factories/{factory_slug}/devices/{device_key}/...    │
└─────────────────────────────────────────────────────────────────────────┘
                      ▲
                      │
           ┌──────────┴──────────┐
           │                     │
      ┌────────┐            ┌────────┐
      │Device  │            │Device  │
      │  M01   │            │  M02   │
      │(Comp-  │            │(Pump)  │
      │ ressor)│            │        │
      └────────┘            └────────┘
```

### 2.2 Service Explanations

#### **NGINX (Port 80/443)**
- **What**: Reverse proxy and TLS termination
- **Why**: Handles HTTPS encryption, rate limiting, static file serving
- **Connects to**: API service (port 8000), Frontend static files
- **Configuration**: `nginx/nginx.conf` (dev), `nginx/nginx.prod.conf` (production with TLS)

#### **Frontend (React SPA)**
- **What**: Single-page application built with React, TypeScript, Vite
- **Why**: Modern, responsive UI for factory monitoring
- **Port**: Served as static files via NGINX
- **Tech Stack**: React 18, TypeScript, TailwindCSS, Recharts, Zustand
- **Talks to**: API service via `/api/v1/*` endpoints

#### **API Service (FastAPI on port 8000)**
- **What**: RESTful API server handling all business logic
- **Why**: FastAPI provides async support, auto-generated docs, Pydantic validation
- **Port**: 8000 (internal), exposed via NGINX
- **Tech Stack**: FastAPI, SQLAlchemy (async), Pydantic, bcrypt, JWT
- **Talks to**: MySQL, InfluxDB, Redis, MinIO, Celery
- **Entry Point**: `backend/app/main.py`

#### **Telemetry Service (Python MQTT Subscriber)**
- **What**: Dedicated service that consumes MQTT messages and ingests telemetry
- **Why**: Isolated from API to ensure telemetry pipeline never blocks web requests
- **Port**: N/A (MQTT client, not HTTP server)
- **Tech Stack**: aiomqtt, asyncio, SQLAlchemy, InfluxDB client
- **Talks to**: EMQX (MQTT), MySQL, Redis, InfluxDB, Celery
- **Entry Point**: `telemetry/main.py`

#### **Celery Workers (4 Background Task Queues)**
- **What**: Asynchronous task processors for long-running operations
- **Why**: Offload rule evaluation, analytics, reporting, notifications from request/response cycle
- **Queues**:
  - `rules`: Rule evaluation (triggered by telemetry)
  - `analytics`: ML jobs (anomaly detection, forecasting)
  - `reporting`: Report generation (PDF, Excel)
  - `notifications`: Email and WhatsApp alerts
- **Broker**: Redis (queues in DB 1)
- **Results**: Redis (results in DB 2)
- **Entry Point**: `backend/app/workers/celery_app.py`

#### **MySQL (Port 3306)**
- **What**: Relational database for metadata
- **Why**: ACID transactions, relational integrity for structured data
- **Stores**: Factories, users, devices, device_parameters, rules, alerts, analytics_jobs, reports
- **Does NOT store**: Time-series telemetry (that's in InfluxDB)
- **Schema**: Defined in `backend/alembic/versions/41d31b3cb96e_initial_schema.py`

#### **InfluxDB (Port 8086)**
- **What**: Time-series database for telemetry
- **Why**: Optimized for high-write, time-based queries with automatic downsampling
- **Stores**: Measurement `device_metrics` with tags (factory_id, device_id, parameter) and field `_value`
- **Schema**: Schema-free, auto-discovers parameters from incoming data
- **Retention**: Configurable (default: infinite, production: 90 days with downsampling)

#### **Redis (Port 6379)**
- **What**: In-memory cache and message broker
- **Why**: Fast lookups, Celery broker/backend
- **Uses**:
  - DB 0: Application cache (factory lookup, device lookup)
  - DB 1: Celery broker (task queues)
  - DB 2: Celery results backend (task status/results)
- **TTL**: Factory cache = 3600s, Device cache = 1800s

#### **MinIO (Port 9000)**
- **What**: S3-compatible object storage
- **Why**: Store large binary files (reports, analytics results) outside database
- **Bucket**: `factoryops`
- **Directory Structure**:
  - `{factory_id}/reports/{report_id}.pdf`
  - `{factory_id}/analytics/{job_id}.json`
- **Access**: Pre-signed URLs (24h expiry for reports, 7d for analytics)

#### **EMQX (Port 1883)**
- **What**: MQTT broker for IoT device communication
- **Why**: Lightweight pub/sub protocol ideal for constrained devices
- **Topics**: `factories/{factory_slug}/devices/{device_key}/telemetry`
- **Security**: Optional username/password (configured via env vars)

### 2.3 Technology Stack with Reasoning

| Component | Technology | Version | Why This Choice |
|-----------|-----------|---------|-----------------|
| **Backend API** | FastAPI | Latest | Async support, auto OpenAPI docs, Pydantic validation |
| **Backend Language** | Python | 3.11 | Rich ML/analytics ecosystem, async/await support |
| **ORM** | SQLAlchemy | 2.x (async) | Industry standard, async support, type hints |
| **Database** | MySQL | 8.0 | Proven reliability, ACID transactions, JSON column support |
| **Time-Series DB** | InfluxDB | 2.7 | Purpose-built for time-series, Flux query language |
| **Cache/Queue** | Redis | 7.x | High performance, pub/sub, Celery integration |
| **Object Storage** | MinIO | Latest | S3-compatible, self-hosted, multi-tenant support |
| **MQTT Broker** | EMQX | Latest | Scalable, cluster support, dashboard UI |
| **Task Queue** | Celery | Latest | Battle-tested, multi-queue support, retries |
| **Frontend** | React | 18.x | Component reusability, large ecosystem |
| **Frontend Language** | TypeScript | 5.x | Type safety, better IDE support |
| **Build Tool** | Vite | Latest | Fast HMR, modern ESM support |
| **UI Framework** | TailwindCSS | 3.x | Utility-first, rapid prototyping |
| **Charts** | Recharts | Latest | React-native, composable, responsive |
| **State Management** | Zustand | Latest | Lightweight, TypeScript-friendly |
| **HTTP Client** | Axios | Latest | Interceptors, request/response transformation |
| **Authentication** | JWT | - | Stateless, factory_id embedded in token |
| **Password Hashing** | bcrypt | - | Adaptive cost factor, industry standard |
| **Migrations** | Alembic | Latest | SQLAlchemy integration, reversible migrations |
| **Testing** | pytest | Latest | Async support, fixtures, parametrization |
| **Logging** | structlog | Latest | Structured JSON logs, context propagation |
| **Metrics** | Prometheus | - | Industry standard, pull-based, Grafana integration |

---

## 3. Data Architecture

### 3.1 MySQL Database Schema

#### Table: `factories`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INT | NO | AUTO_INCREMENT | Primary key |
| `name` | VARCHAR(255) | NO | - | Factory display name (e.g., "VPC Factory") |
| `slug` | VARCHAR(100) | NO | - | URL-safe identifier (e.g., "vpc"), **UNIQUE** |
| `timezone` | VARCHAR(100) | NO | 'UTC' | Timezone for date/time display |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | Last update timestamp |

**Indexes:**
- PRIMARY KEY (`id`)
- UNIQUE KEY (`slug`)

**Relationships:**
- One-to-many with `users`, `devices`, `rules`, `alerts`, `analytics_jobs`, `reports`

---

#### Table: `users`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INT | NO | AUTO_INCREMENT | Primary key |
| `factory_id` | INT | NO | - | Foreign key to `factories.id` |
| `email` | VARCHAR(255) | NO | - | User email address |
| `whatsapp_number` | VARCHAR(50) | YES | NULL | WhatsApp number for notifications (E.164 format) |
| `hashed_password` | VARCHAR(255) | NO | - | bcrypt hashed password |
| `role` | ENUM('super_admin', 'admin') | NO | 'admin' | User role |
| `permissions` | JSON | YES | NULL | Permission flags: `{"can_create_rules": true, "can_run_analytics": true, "can_generate_reports": true}` |
| `is_active` | BOOLEAN | NO | TRUE | Active status (soft delete flag) |
| `invite_token` | VARCHAR(255) | YES | NULL | Invitation token for new users |
| `invited_at` | DATETIME | YES | NULL | When invitation was sent |
| `last_login` | DATETIME | YES | NULL | Last successful login timestamp |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- PRIMARY KEY (`id`)
- INDEX (`factory_id`)

**Relationships:**
- Many-to-one with `factories`

**Business Rules:**
- `super_admin` has all permissions, bypasses permission checks
- `invite_token` expires after 48 hours
- Inactive users cannot log in

---

#### Table: `devices`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INT | NO | AUTO_INCREMENT | Primary key |
| `factory_id` | INT | NO | - | Foreign key to `factories.id` |
| `device_key` | VARCHAR(100) | NO | - | Device identifier (e.g., "M01"), unique per factory |
| `name` | VARCHAR(255) | YES | NULL | Human-readable name (e.g., "Compressor 1") |
| `manufacturer` | VARCHAR(255) | YES | NULL | Equipment manufacturer (e.g., "Siemens") |
| `model` | VARCHAR(255) | YES | NULL | Equipment model number |
| `region` | VARCHAR(255) | YES | NULL | Physical location (e.g., "Zone A", "Building 2") |
| `api_key` | VARCHAR(255) | YES | NULL | API key for device authentication (auto-generated) |
| `is_active` | BOOLEAN | NO | TRUE | Active status (soft delete flag) |
| `last_seen` | DATETIME | YES | NULL | Last telemetry reception timestamp |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | Last update timestamp |

**Indexes:**
- PRIMARY KEY (`id`)
- INDEX (`factory_id`)
- UNIQUE INDEX (`factory_id`, `device_key`)

**Relationships:**
- Many-to-one with `factories`
- One-to-many with `device_parameters`, `alerts`
- Many-to-many with `rules` (via `rule_devices`)

**Business Rules:**
- `device_key` must be unique within a factory (not globally)
- Device is "online" if `last_seen` < 10 minutes ago
- Auto-created on first telemetry message if doesn't exist

---

#### Table: `device_parameters`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INT | NO | AUTO_INCREMENT | Primary key |
| `factory_id` | INT | NO | - | Foreign key to `factories.id` |
| `device_id` | INT | NO | - | Foreign key to `devices.id` |
| `parameter_key` | VARCHAR(100) | NO | - | Parameter identifier (e.g., "voltage", "temperature") |
| `display_name` | VARCHAR(255) | YES | NULL | Human-readable name (e.g., "Voltage (V)") |
| `unit` | VARCHAR(50) | YES | NULL | Unit of measurement (e.g., "V", "°C", "kW") |
| `data_type` | ENUM('float', 'int', 'string') | NO | 'float' | Data type of parameter value |
| `is_kpi_selected` | BOOLEAN | NO | TRUE | Whether to display as KPI on dashboard |
| `discovered_at` | DATETIME | NO | CURRENT_TIMESTAMP | When parameter was first discovered |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | Last update timestamp |

**Indexes:**
- PRIMARY KEY (`id`)
- INDEX (`factory_id`, `device_id`)
- UNIQUE INDEX (`device_id`, `parameter_key`)

**Relationships:**
- Many-to-one with `devices`

**Business Rules:**
- Auto-discovered on first telemetry message containing new parameter
- Idempotent upsert: `discovered_at` never changes, `updated_at` refreshed on each telemetry
- `parameter_key` must be unique per device (not per factory)

---

#### Table: `rules`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INT | NO | AUTO_INCREMENT | Primary key |
| `factory_id` | INT | NO | - | Foreign key to `factories.id` |
| `name` | VARCHAR(255) | NO | - | Rule name (e.g., "High Voltage Alert") |
| `description` | TEXT | YES | NULL | Rule description |
| `scope` | ENUM('device', 'global') | NO | 'device' | Whether rule applies to specific devices or all devices |
| `conditions` | JSON | NO | - | Condition tree (see format below) |
| `cooldown_minutes` | INT | YES | 15 | Minimum minutes between repeat alerts for same device |
| `is_active` | BOOLEAN | NO | TRUE | Whether rule is enabled |
| `schedule_type` | ENUM('always', 'time_window', 'date_range') | NO | 'always' | When rule should be evaluated |
| `schedule_config` | JSON | YES | NULL | Schedule configuration (see format below) |
| `severity` | ENUM('low', 'medium', 'high', 'critical') | NO | 'medium' | Alert severity |
| `notification_channels` | JSON | YES | NULL | Notification settings: `{"email": true, "whatsapp": false}` |
| `created_by` | INT | YES | NULL | Foreign key to `users.id` (creator) |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | Last update timestamp |

**Indexes:**
- PRIMARY KEY (`id`)
- INDEX (`factory_id`, `is_active`)

**Relationships:**
- Many-to-one with `factories`
- Many-to-many with `devices` (via `rule_devices`)
- One-to-many with `alerts`

**Condition Format (JSON):**
```json
{
  "operator": "AND",
  "conditions": [
    {
      "parameter": "voltage",
      "operator": "gt",
      "value": 240
    },
    {
      "operator": "OR",
      "conditions": [
        {"parameter": "current", "operator": "gt", "value": 15},
        {"parameter": "power", "operator": "gt", "value": 5000}
      ]
    }
  ]
}
```

**Schedule Config Examples:**
- Time window: `{"start_time": "08:00", "end_time": "18:00", "days": [1, 2, 3, 4, 5]}`  (Mon-Fri 8am-6pm)
- Date range: `{"start_date": "2026-01-01", "end_date": "2026-03-31"}`

---

#### Table: `rule_devices` (Association Table)
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `rule_id` | INT | NO | - | Foreign key to `rules.id` |
| `device_id` | INT | NO | - | Foreign key to `devices.id` |

**Indexes:**
- PRIMARY KEY (`rule_id`, `device_id`)

**Purpose:** Many-to-many relationship between rules and devices

---

#### Table: `rule_cooldowns`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `rule_id` | INT | NO | - | Foreign key to `rules.id` |
| `device_id` | INT | NO | - | Foreign key to `devices.id` |
| `last_triggered` | DATETIME | NO | - | When alert was last triggered |

**Indexes:**
- PRIMARY KEY (`rule_id`, `device_id`)

**Purpose:** Track last trigger time to enforce cooldown periods

---

#### Table: `alerts`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INT | NO | AUTO_INCREMENT | Primary key |
| `factory_id` | INT | NO | - | Foreign key to `factories.id` |
| `rule_id` | INT | NO | - | Foreign key to `rules.id` |
| `device_id` | INT | NO | - | Foreign key to `devices.id` |
| `triggered_at` | DATETIME | NO | - | When alert was triggered |
| `resolved_at` | DATETIME | YES | NULL | When alert was resolved (NULL = unresolved) |
| `severity` | ENUM('low', 'medium', 'high', 'critical') | NO | - | Alert severity (copied from rule) |
| `message` | TEXT | YES | NULL | Human-readable alert message |
| `telemetry_snapshot` | JSON | YES | NULL | Telemetry values at trigger time |
| `notification_sent` | BOOLEAN | NO | FALSE | Whether notification was successfully sent |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- PRIMARY KEY (`id`)
- INDEX (`factory_id`, `device_id`, `triggered_at`)
- INDEX (`factory_id`, `triggered_at`)

**Relationships:**
- Many-to-one with `factories`, `rules`, `devices`

---

#### Table: `analytics_jobs`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | VARCHAR(36) | NO | - | UUID primary key |
| `factory_id` | INT | NO | - | Foreign key to `factories.id` |
| `created_by` | INT | NO | - | Foreign key to `users.id` |
| `job_type` | ENUM('anomaly', 'failure_prediction', 'energy_forecast', 'ai_copilot') | NO | - | Type of analytics job |
| `mode` | ENUM('standard', 'ai_copilot') | NO | 'standard' | Job mode |
| `device_ids` | JSON | NO | - | Array of device IDs to analyze |
| `date_range_start` | DATETIME | NO | - | Analysis start date |
| `date_range_end` | DATETIME | NO | - | Analysis end date |
| `status` | ENUM('pending', 'running', 'complete', 'failed') | NO | 'pending' | Job status |
| `result_url` | VARCHAR(500) | YES | NULL | Pre-signed URL to result file in MinIO |
| `error_message` | TEXT | YES | NULL | Error message if failed |
| `started_at` | DATETIME | YES | NULL | When job processing started |
| `completed_at` | DATETIME | YES | NULL | When job finished |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- PRIMARY KEY (`id`)
- INDEX (`factory_id`, `status`)

**Relationships:**
- Many-to-one with `factories`

---

#### Table: `reports`
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | VARCHAR(36) | NO | - | UUID primary key |
| `factory_id` | INT | NO | - | Foreign key to `factories.id` |
| `created_by` | INT | NO | - | Foreign key to `users.id` |
| `title` | VARCHAR(255) | YES | NULL | Report title |
| `device_ids` | JSON | NO | - | Array of device IDs included in report |
| `date_range_start` | DATETIME | NO | - | Report start date |
| `date_range_end` | DATETIME | NO | - | Report end date |
| `format` | ENUM('pdf', 'excel', 'json') | NO | - | Report file format |
| `include_analytics` | BOOLEAN | NO | FALSE | Whether to include analytics results |
| `analytics_job_id` | VARCHAR(36) | YES | NULL | Foreign key to `analytics_jobs.id` |
| `status` | ENUM('pending', 'running', 'complete', 'failed') | NO | 'pending' | Report generation status |
| `file_url` | VARCHAR(500) | YES | NULL | Pre-signed URL to file in MinIO |
| `file_size_bytes` | BIGINT | YES | NULL | File size in bytes |
| `error_message` | TEXT | YES | NULL | Error message if failed |
| `expires_at` | DATETIME | YES | NULL | When pre-signed URL expires |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- PRIMARY KEY (`id`)

**Relationships:**
- Many-to-one with `factories`

---

### 3.2 InfluxDB Schema

**Measurement:** `device_metrics`

**Tags (Indexed):**
| Tag | Type | Description | Example |
|-----|------|-------------|---------|
| `factory_id` | String | Factory ID (from MySQL) | `"1"` |
| `device_id` | String | Device ID (from MySQL) | `"5"` |
| `parameter` | String | Parameter key | `"voltage"` |

**Field:**
| Field | Type | Description |
|-------|------|-------------|
| `_value` | Float | Metric value | `231.4` |

**Timestamp:** Nanosecond-precision timestamp (auto-indexed)

**Example Data Point:**
```
device_metrics,factory_id=1,device_id=5,parameter=voltage _value=231.4 1704067200000000000
device_metrics,factory_id=1,device_id=5,parameter=current _value=3.2 1704067200000000000
device_metrics,factory_id=1,device_id=5,parameter=power _value=745.6 1704067200000000000
```

**Retention Policy:** Default (infinite), production recommended 90 days with downsampling

**Query Examples:**
```flux
// Get last 5 minutes of voltage for device 5
from(bucket: "factoryops")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "1")
  |> filter(fn: (r) => r.device_id == "5")
  |> filter(fn: (r) => r.parameter == "voltage")

// Get hourly average power for last 24 hours
from(bucket: "factoryops")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> filter(fn: (r) => r.factory_id == "1")
  |> filter(fn: (r) => r.parameter == "power")
  |> aggregateWindow(every: 1h, fn: mean)
```

---

### 3.3 Redis Usage

**Database 0 (Application Cache):**

| Key Pattern | Type | TTL | Value | Purpose |
|-------------|------|-----|-------|---------|
| `factory:slug:{slug}` | String | 3600s | JSON-serialized Factory object | Factory lookup by slug |
| `device:{factory_id}:{device_key}` | String | 1800s | JSON-serialized Device object | Device lookup |

**Database 1 (Celery Broker):**
- Queue keys managed by Celery
- Task states stored temporarily

**Database 2 (Celery Results):**
- Task result keys: `celery-task-meta-{task_id}`
- TTL: 3600s

---

### 3.4 MinIO (S3) Structure

**Bucket:** `factoryops`

**Directory Layout:**
```
factoryops/
├── 1/                          # factory_id
│   ├── reports/
│   │   ├── uuid-1.pdf
│   │   ├── uuid-2.xlsx
│   │   └── uuid-3.json
│   └── analytics/
│       ├── uuid-4.json         # Anomaly detection results
│       └── uuid-5.json         # Forecast results
├── 2/                          # another factory_id
│   └── reports/
│       └── uuid-6.pdf
```

**Access Method:** Pre-signed URLs with expiration
- Reports: 24 hours
- Analytics: 7 days

---

## 4. Complete Data Flows

### 4.1 Flow 1: Device Sends Telemetry → MQTT → Telemetry Service → InfluxDB + MySQL

**Scenario:** Device M01 sends voltage=231.4V, current=3.2A to the system

**Step-by-Step Flow:**

```
┌─────────────┐
│  Device M01 │
│  (Hardware) │
└──────┬──────┘
       │
       │ 1. Publishes MQTT message
       │    Topic: factories/vpc/devices/M01/telemetry
       │    Payload: {"metrics": {"voltage": 231.4, "current": 3.2}}
       ▼
┌─────────────────────────────────────────────────────────────┐
│                      EMQX Broker                            │
│  • Receives message on port 1883                            │
│  • Broadcasts to all subscribers of matching topic          │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ 2. Delivers message to subscriber
       ▼
┌─────────────────────────────────────────────────────────────┐
│           Telemetry Service (subscriber.py)                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ MQTT Subscriber Loop (infinite loop, never crashes)    ││
│  │ • Subscribed to: factories/+/devices/+/telemetry       ││
│  │ • Receives message                                     ││
│  │ • Calls: process_telemetry(topic, payload, db, ...)   ││
│  └─────────────────────────────────────────────────────────┘│
└──────┬──────────────────────────────────────────────────────┘
       │
       │ 3. Enter ingestion pipeline
       ▼
┌─────────────────────────────────────────────────────────────┐
│         handlers/ingestion.py: process_telemetry()          │
│                                                              │
│  Step 3a: Parse topic                                       │
│  • parse_topic("factories/vpc/devices/M01/telemetry")       │
│  • Extract: factory_slug = "vpc", device_key = "M01"        │
│                                                              │
│  Step 3b: Validate payload schema                           │
│  • TelemetryPayload.model_validate_json(payload)            │
│  • Validates: metrics is dict, timestamp optional           │
│  • Result: data = TelemetryPayload(metrics={...})           │
│                                                              │
│  Step 3c: Resolve factory (cache-first)                     │
│  • Check Redis: GET factory:slug:vpc                        │
│  • If miss: Query MySQL SELECT * FROM factories WHERE slug='vpc'│
│  • Cache result in Redis with 3600s TTL                     │
│  • If not found: Log warning and RETURN (discard message)   │
│  • Result: factory = Factory(id=1, name="VPC Factory")      │
│                                                              │
│  Step 3d: Get or create device (cache-first)                │
│  • Check Redis: GET device:1:M01                            │
│  • If miss: Query MySQL SELECT * FROM devices WHERE         │
│              factory_id=1 AND device_key='M01'              │
│  • If not found: Auto-create device with name=device_key    │
│  • Cache result in Redis with 1800s TTL                     │
│  • Result: device = Device(id=5, factory_id=1, key="M01")   │
│                                                              │
│  Step 3e: Discover parameters (idempotent upsert)           │
│  • For each key in metrics: ["voltage", "current"]          │
│  • Check if exists: SELECT FROM device_parameters WHERE     │
│                     device_id=5 AND parameter_key='voltage' │
│  • If not exists: INSERT INTO device_parameters             │
│                   (factory_id=1, device_id=5,               │
│                    parameter_key='voltage', data_type='float',│
│                    is_kpi_selected=true)                    │
│  • If exists: UPDATE updated_at = NOW()                     │
│  • Result: Parameters registered in MySQL                   │
│                                                              │
│  Step 3f: Write to InfluxDB (batch)                         │
│  • Build points:                                            │
│    [                                                         │
│      Point("device_metrics")                                │
│        .tag("factory_id", "1")                              │
│        .tag("device_id", "5")                               │
│        .tag("parameter", "voltage")                         │
│        .field("_value", 231.4)                              │
│        .time(datetime.utcnow()),                            │
│      Point("device_metrics")                                │
│        .tag("factory_id", "1")                              │
│        .tag("device_id", "5")                               │
│        .tag("parameter", "current")                         │
│        .field("_value", 3.2)                                │
│        .time(datetime.utcnow())                             │
│    ]                                                         │
│  • influx_write_api.write(points)                           │
│  • Result: Data persisted in InfluxDB                       │
│                                                              │
│  Step 3g: Update device.last_seen                           │
│  • UPDATE devices SET last_seen=NOW() WHERE id=5            │
│  • Result: Device shows as "online" in UI                   │
│                                                              │
│  Step 3h: Dispatch rule evaluation (async, non-blocking)    │
│  • evaluate_rules_task.delay(                               │
│      factory_id=1,                                          │
│      device_id=5,                                           │
│      metrics={"voltage": 231.4, "current": 3.2},            │
│      timestamp="2026-02-19T10:30:00Z"                       │
│    )                                                         │
│  • Result: Celery task queued in Redis (rules queue)        │
│                                                              │
│  Step 3i: Log success                                       │
│  • logger.info("telemetry.processed", factory_id=1, ...)    │
│  • Prometheus counter: telemetry_messages_total{factory_id="1"}.inc()│
│                                                              │
└─────────────────────────────────────────────────────────────┘
       │
       │ 4. Rule evaluation (asynchronous)
       ▼
┌─────────────────────────────────────────────────────────────┐
│         Celery Worker (rules queue)                         │
│  • Picks up task from Redis queue                           │
│  • Calls: evaluate_rules_task(factory_id=1, device_id=5,...)│
│  • Fetches active rules for device 5                        │
│  • Evaluates conditions against metrics                     │
│  • If condition matches: Creates alert, sends notification  │
└─────────────────────────────────────────────────────────────┘
```

**Total Latency:** ~50-200ms (MQTT → InfluxDB write)

**Failure Handling:**
- If InfluxDB write fails → Log error, continue (don't crash)
- If MySQL query fails → Log error, continue (don't crash)
- If Redis is down → Fallback to MySQL, continue
- If rule dispatch fails → Log warning, continue (telemetry still saved)
- **Critical:** process_telemetry() catches ALL exceptions, never propagates to MQTT loop

---

### 4.2 Flow 2: User Logs In → JWT Issued → API Call Authorized

**Scenario:** User admin@vpc.com logs in and accesses dashboard

**Step 1: Factory Selection**
```
Frontend (FactorySelect.tsx)
│
├─ User selects factory from dropdown
│
└─ Redirects to /login?factory=vpc
```

**Step 2: Login**
```
Frontend (Login.tsx)
│
├─ User enters email + password
│
└─ POST /api/v1/auth/login
    Body: {
      "factory_slug": "vpc",
      "email": "admin@vpc.com",
      "password": "Admin@123"
    }
    
    ↓
    
API (auth.py: login endpoint)
│
├─ Step 2a: Validate factory exists
│   SELECT * FROM factories WHERE slug = 'vpc'
│   → factory_id = 1
│
├─ Step 2b: Validate user exists and belongs to factory
│   SELECT * FROM users WHERE factory_id = 1 AND email = 'admin@vpc.com'
│   → user_id = 10, hashed_password = '$2b$12...'
│
├─ Step 2c: Verify password
│   bcrypt.checkpw('Admin@123', hashed_password)
│   → Returns True
│
├─ Step 2d: Update last_login
│   UPDATE users SET last_login = NOW() WHERE id = 10
│
├─ Step 2e: Generate JWT token
│   create_access_token(
│     user_id=10,
│     factory_id=1,
│     factory_slug='vpc',
│     role='super_admin'
│   )
│   
│   Token payload:
│   {
│     "sub": "10",              # user_id
│     "factory_id": 1,          # CRITICAL: embedded in token
│     "factory_slug": "vpc",
│     "role": "super_admin",
│     "iat": 1704067200,         # issued at
│     "exp": 1704153600          # expires (24h later)
│   }
│   
│   → Signed with JWT_SECRET_KEY
│
└─ Step 2f: Return token
    Response: {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "factory": {"id": 1, "name": "VPC Factory", "slug": "vpc"},
      "user": {"id": 10, "email": "admin@vpc.com", "role": "super_admin"}
    }
    
    ↓
    
Frontend (authStore.ts)
│
├─ Stores token in localStorage
└─ Sets Authorization header for all future requests:
    axios.defaults.headers.common['Authorization'] = 'Bearer eyJ...'
```

**Step 3: API Call with Authorization**
```
Frontend (Dashboard.tsx)
│
└─ useEffect: Fetch dashboard summary
    GET /api/v1/dashboard/summary
    Headers: {
      "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    
    ↓
    
API (dependencies.py: get_current_user dependency)
│
├─ Step 3a: Extract token from Authorization header
│   token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
│
├─ Step 3b: Decode and validate JWT
│   payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
│   
│   Checks:
│   • Signature valid? (ensures token not tampered)
│   • Expiration valid? (exp > now)
│   
│   If invalid → Raise HTTPException(401, "Invalid or expired token")
│   
│   Result: payload = {
│     "sub": "10",
│     "factory_id": 1,
│     "factory_slug": "vpc",
│     "role": "super_admin",
│     ...
│   }
│
├─ Step 3c: Fetch user from database
│   user_id = int(payload["sub"])  # 10
│   SELECT * FROM users WHERE id = 10
│   
│   If not found or is_active=false → Raise HTTPException(401)
│
├─ Step 3d: Attach factory_id to user object
│   user._token_factory_id = payload["factory_id"]  # 1
│   user._token_factory_slug = payload["factory_slug"]  # "vpc"
│   user._token_role = payload["role"]  # "super_admin"
│
└─ Step 3e: Return user object
    → Passed to endpoint handler as `user: User = Depends(get_current_user)`
    
    ↓
    
API (dashboard.py: get_dashboard_summary endpoint)
│
├─ Extracts factory_id from authenticated user:
│   factory_id = user._token_factory_id  # 1
│
├─ Queries data with factory_id filter:
│   SELECT COUNT(*) FROM devices WHERE factory_id = 1
│   SELECT COUNT(*) FROM alerts WHERE factory_id = 1 AND resolved_at IS NULL
│   
│   InfluxDB query with factory_id filter:
│   from(bucket: "factoryops")
│     |> range(start: -5m)
│     |> filter(fn: (r) => r.factory_id == "1")  # CRITICAL FILTER
│     |> filter(fn: (r) => r.parameter == "power")
│     |> last()
│
└─ Returns JSON response with dashboard data
    
    ↓
    
Frontend receives response and renders dashboard
```

**Security Guarantees:**
- Factory ID comes from JWT (signed), **never from request body**
- User cannot access data from other factories (different factory_id in token)
- Token expires after 24 hours → Must re-login
- All API routes use `Depends(get_current_user)` → Automatic authentication

---

### 4.3 Flow 3: Alert Rule Triggers → Notification Sent

**Scenario:** Voltage exceeds 240V, triggering "High Voltage" rule

**Step 1: Telemetry Arrives**
```
Device publishes: {"metrics": {"voltage": 245.2, "current": 3.5}}
→ Telemetry service processes (see Flow 1)
→ Dispatches: evaluate_rules_task.delay(factory_id=1, device_id=5, metrics={...})
```

**Step 2: Celery Worker Picks Up Task**
```
Celery Worker (rules queue)
│
├─ Retrieves task from Redis queue
│
└─ Executes: evaluate_rules_task(
      factory_id=1,
      device_id=5,
      metrics={"voltage": 245.2, "current": 3.5},
      timestamp="2026-02-19T10:35:00Z"
    )
```

**Step 3: Fetch Active Rules**
```
rule_engine.py
│
├─ Query: SELECT * FROM rules
│          JOIN rule_devices ON rules.id = rule_devices.rule_id
│          WHERE rules.factory_id = 1
│            AND rule_devices.device_id = 5
│            AND rules.is_active = true
│
└─ Result: [
      {
        "id": 42,
        "name": "High Voltage Alert",
        "conditions": {
          "operator": "AND",
          "conditions": [
            {"parameter": "voltage", "operator": "gt", "value": 240}
          ]
        },
        "cooldown_minutes": 15,
        "severity": "critical",
        "notification_channels": {"email": true, "whatsapp": true}
      }
    ]
```

**Step 4: Evaluate Each Rule**
```
For rule "High Voltage Alert":
│
├─ Step 4a: Check schedule
│   is_rule_scheduled(rule, now)
│   → schedule_type = "always" → Returns True
│
├─ Step 4b: Check cooldown
│   SELECT * FROM rule_cooldowns WHERE rule_id=42 AND device_id=5
│   → last_triggered = 2026-02-19T09:00:00Z (95 minutes ago)
│   → cooldown_minutes = 15
│   → Elapsed (95) > Cooldown (15) → Returns False (not in cooldown)
│
├─ Step 4c: Evaluate conditions
│   evaluate_conditions(
│     condition_tree={
│       "operator": "AND",
│       "conditions": [
│         {"parameter": "voltage", "operator": "gt", "value": 240}
│       ]
│     },
│     metrics={"voltage": 245.2, "current": 3.5}
│   )
│   
│   Evaluation:
│   • Get "voltage" from metrics → 245.2
│   • Apply operator "gt" (greater than) → 245.2 > 240 → True
│   • AND operator with [True] → True
│   
│   → Returns True (condition matched!)
│
├─ Step 4d: Create alert
│   INSERT INTO alerts (
│     factory_id=1,
│     rule_id=42,
│     device_id=5,
│     triggered_at='2026-02-19T10:35:00Z',
│     severity='critical',
│     message='[High Voltage Alert] voltage (245.2) gt 240',
│     telemetry_snapshot='{"voltage": 245.2, "current": 3.5}',
│     notification_sent=false
│   )
│   → alert_id = 1001
│
├─ Step 4e: Update cooldown
│   INSERT INTO rule_cooldowns (rule_id=42, device_id=5, last_triggered=NOW())
│   ON DUPLICATE KEY UPDATE last_triggered=NOW()
│   → Prevents repeat alerts for next 15 minutes
│
├─ Step 4f: Dispatch notification task
│   send_notifications_task.delay(
│     alert_id=1001,
│     channels={"email": true, "whatsapp": true}
│   )
│   → Queued in Redis (notifications queue)
│
└─ Step 4g: Log and increment metrics
    logger.info("alert.triggered", factory_id=1, alert_id=1001, severity="critical")
    Prometheus: alerts_triggered_total{factory_id="1", severity="critical"}.inc()
```

**Step 5: Send Notifications (Separate Task)**
```
Celery Worker (notifications queue)
│
├─ Picks up task: send_notifications_task(alert_id=1001, channels={...})
│
├─ Step 5a: Fetch alert details
│   SELECT alerts.*, rules.name, devices.name
│   FROM alerts
│   JOIN rules ON alerts.rule_id = rules.id
│   JOIN devices ON alerts.device_id = devices.id
│   WHERE alerts.id = 1001
│   
│   Result: {
│     "id": 1001,
│     "factory_id": 1,
│     "rule_name": "High Voltage Alert",
│     "device_name": "Compressor 1",
│     "severity": "critical",
│     "message": "[High Voltage Alert] voltage (245.2) gt 240",
│     "triggered_at": "2026-02-19T10:35:00Z",
│     "telemetry_snapshot": {"voltage": 245.2, "current": 3.5}
│   }
│
├─ Step 5b: Fetch factory users
│   SELECT email, whatsapp_number FROM users
│   WHERE factory_id = 1 AND is_active = true
│   
│   Result: [
│     {"email": "admin@vpc.com", "whatsapp_number": "+919876543210"},
│     {"email": "operator@vpc.com", "whatsapp_number": null}
│   ]
│
├─ Step 5c: Send email notifications (if channel enabled)
│   For each user with email:
│   │
│   ├─ Compose email:
│   │   From: noreply@factoryops.local
│   │   To: admin@vpc.com
│   │   Subject: [CRITICAL] Alert: High Voltage Alert
│   │   Body:
│   │     Rule: High Voltage Alert
│   │     Device: Compressor 1 (M01)
│   │     Severity: CRITICAL
│   │     Triggered: 2026-02-19 10:35:00
│   │     
│   │     Message:
│   │     [High Voltage Alert] voltage (245.2) gt 240
│   │     
│   │     Telemetry Snapshot:
│   │     {"voltage": 245.2, "current": 3.5}
│   │
│   ├─ Send via SMTP:
│   │   smtp.SMTP(settings.smtp_host, settings.smtp_port)
│   │   smtp.starttls()
│   │   smtp.login(settings.smtp_user, settings.smtp_password)
│   │   smtp.send_message(msg)
│   │
│   ├─ Log success:
│   │   logger.info("notification.email_sent", alert_id=1001, to_email="adm***@vpc.com")
│   │   Prometheus: notifications_sent_total{channel="email", status="success"}.inc()
│   │
│   └─ Handle errors gracefully (don't fail entire task if one email fails)
│
├─ Step 5d: Send WhatsApp notifications (if channel enabled)
│   For each user with whatsapp_number:
│   │
│   ├─ Create Twilio client:
│   │   client = TwilioClient(account_sid, auth_token)
│   │
│   ├─ Format message:
│   │   🚨 *CRITICAL ALERT*
│   │   
│   │   *Rule:* High Voltage Alert
│   │   *Device:* Compressor 1
│   │   *Time:* 2026-02-19 10:35:00
│   │   
│   │   [High Voltage Alert] voltage (245.2) gt 240
│   │
│   ├─ Send message:
│   │   client.messages.create(
│   │     from_="whatsapp:+14155238886",
│   │     to="whatsapp:+919876543210",
│   │     body=message_body
│   │   )
│   │
│   ├─ Log success:
│   │   logger.info("notification.whatsapp_sent", alert_id=1001, to_number="+919***210")
│   │   Prometheus: notifications_sent_total{channel="whatsapp", status="success"}.inc()
│   │
│   └─ Handle errors gracefully
│
└─ Step 5e: Mark alert as notified
    UPDATE alerts SET notification_sent = true WHERE id = 1001
    
    logger.info("notification.completed", alert_id=1001, user_count=2)
```

**Step 6: Frontend Sees New Alert**
```
Frontend polls: GET /api/v1/alerts?page=1&per_page=20
│
├─ API filters by factory_id from JWT:
│   SELECT * FROM alerts WHERE factory_id = 1 ORDER BY triggered_at DESC LIMIT 20
│
└─ Response includes new alert:
    {
      "data": [
        {
          "id": 1001,
          "rule_name": "High Voltage Alert",
          "device_name": "Compressor 1",
          "severity": "critical",
          "message": "[High Voltage Alert] voltage (245.2) gt 240",
          "triggered_at": "2026-02-19T10:35:00Z",
          "resolved_at": null,
          "notification_sent": true
        },
        ...
      ]
    }
    
    ↓
    
Alerts page displays new critical alert with red badge
```

**Total Time:** ~1-5 seconds from telemetry arrival to notification sent

**Error Handling:**
- If one notification fails → Log error, continue with others
- If all notifications fail → Alert still created in database
- If SMTP/Twilio not configured → Log "skipped", don't fail task
- Task retries up to 3 times on failure with exponential backoff

---

### 4.4 Flow 4: Frontend Loads Dashboard → Data Fetched → Displayed

**Scenario:** User navigates to Dashboard page after login

**Step 1: Page Load**
```
User clicks "Dashboard" in sidebar
│
├─ React Router navigates to /dashboard
│
└─ Dashboard.tsx component mounts
```

**Step 2: Data Fetching (Parallel Requests)**
```
Dashboard.tsx useEffect()
│
├─ Request 1: GET /api/v1/dashboard/summary
│   → Fetches aggregate metrics (device count, alerts, energy)
│
└─ Request 2: GET /api/v1/alerts?page=1&per_page=5
    → Fetches recent alerts for activity feed
```

**Step 3: Process Summary Request**
```
API: /api/v1/dashboard/summary
│
├─ Step 3a: Authenticate user (see Flow 2)
│   → factory_id = 1
│
├─ Step 3b: Count total devices
│   SELECT COUNT(*) FROM devices WHERE factory_id = 1
│   → total_devices = 15
│
├─ Step 3c: Count online devices (last_seen < 10 min)
│   SELECT COUNT(*) FROM devices
│   WHERE factory_id = 1
│     AND is_active = true
│     AND last_seen >= NOW() - INTERVAL 10 MINUTE
│   → active_devices = 12
│
├─ Step 3d: Count offline devices
│   offline_devices = total_devices - active_devices
│   → offline_devices = 3
│
├─ Step 3e: Count active alerts
│   SELECT COUNT(*) FROM alerts
│   WHERE factory_id = 1 AND resolved_at IS NULL
│   → active_alerts = 7
│
├─ Step 3f: Count critical alerts
│   SELECT COUNT(*) FROM alerts
│   WHERE factory_id = 1 AND resolved_at IS NULL AND severity = 'critical'
│   → critical_alerts = 2
│
├─ Step 3g: Get current energy consumption (InfluxDB)
│   from(bucket: "factoryops")
│     |> range(start: -5m)
│     |> filter(fn: (r) => r._measurement == "device_metrics")
│     |> filter(fn: (r) => r.factory_id == "1")
│     |> filter(fn: (r) => r.parameter == "power")
│     |> last()
│     |> sum()
│   
│   → current_energy_kw = 127.5
│
├─ Step 3h: Get energy today (InfluxDB)
│   from(bucket: "factoryops")
│     |> range(start: 2026-02-19T00:00:00Z)
│     |> filter(fn: (r) => r._measurement == "device_metrics")
│     |> filter(fn: (r) => r.factory_id == "1")
│     |> filter(fn: (r) => r.parameter == "power")
│     |> aggregateWindow(every: 1h, fn: mean)
│     |> sum()
│   
│   → energy_today_kwh = 1847.2
│
├─ Step 3i: Calculate health score
│   offline_pct = 3/15 = 0.2 (20%)
│   alert_rate = 7/15 = 0.47
│   
│   offline_penalty = min(30, 0.2 * 30) = 6
│   alert_penalty = min(20, 0.47 * 10) = 4.7
│   
│   health_score = 100 - 6 - 4.7 = 89
│   → health_score = 89
│
└─ Step 3j: Return response
    {
      "data": {
        "total_devices": 15,
        "active_devices": 12,
        "offline_devices": 3,
        "active_alerts": 7,
        "critical_alerts": 2,
        "current_energy_kw": 127.5,
        "health_score": 89,
        "energy_today_kwh": 1847.2,
        "energy_this_month_kwh": 42315.7
      }
    }
```

**Step 4: Render Dashboard**
```
Dashboard.tsx receives response
│
├─ Updates state with summary data
│
├─ Renders KPI cards:
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   │ Total Devices   │  │ Active Alerts   │  │ Health Score    │
│   │      15         │  │       7         │  │      89%        │
│   │                 │  │  (2 critical)   │  │  [Progress Bar] │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘
│   
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   │ Current Energy  │  │ Energy Today    │  │ Online Devices  │
│   │   127.5 kW      │  │  1,847.2 kWh    │  │   12 / 15       │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘
│
├─ Renders alerts feed:
│   Recent Alerts:
│   🔴 [CRITICAL] High Voltage Alert - Compressor 1 - 2 min ago
│   🟡 [MEDIUM] High Temperature - Pump 3 - 15 min ago
│   ...
│
└─ Renders energy chart (fetched separately):
    GET /api/v1/devices/5/kpis/history?parameter=power&start=...&end=...
    → Displays 24h power consumption trend
```

**Step 5: Real-Time Updates (Polling)**
```
Dashboard.tsx sets up interval:
│
└─ Every 30 seconds:
    │
    ├─ Re-fetch GET /api/v1/dashboard/summary
    │   → Updates KPI cards with latest values
    │
    └─ Re-fetch GET /api/v1/alerts?page=1&per_page=5
        → Updates alerts feed with new alerts
```

**Performance Optimizations:**
- Dashboard summary query takes ~100-300ms (mostly InfluxDB queries)
- Alerts query uses indexed columns (factory_id, triggered_at) → <50ms
- Redis caching reduces repeated factory/device lookups
- Frontend uses React.memo() to prevent unnecessary re-renders
- Energy charts use auto-selected aggregation intervals (1m/5m/1h/1d)

---

## 5. API Reference

### 5.1 Authentication Endpoints

#### POST /api/v1/auth/factories
**Purpose:** List all available factories  
**Auth Required:** No  
**Request Body:** None  
**Response:**
```json
{
  "data": [
    {"id": 1, "name": "VPC Factory", "slug": "vpc"},
    {"id": 2, "name": "ABC Factory", "slug": "abc"}
  ]
}
```

---

#### POST /api/v1/auth/login
**Purpose:** Authenticate user and receive JWT token  
**Auth Required:** No  
**Request Body:**
```json
{
  "factory_slug": "vpc",
  "email": "admin@vpc.com",
  "password": "Admin@123"
}
```
**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "factory": {"id": 1, "name": "VPC Factory", "slug": "vpc"},
  "user": {
    "id": 10,
    "email": "admin@vpc.com",
    "role": "super_admin",
    "permissions": {"can_create_rules": true, "can_run_analytics": true}
  }
}
```
**Errors:**
- 401: Invalid credentials
- 404: Factory not found

---

### 5.2 Device Endpoints

#### GET /api/v1/devices
**Purpose:** List all devices for current factory (paginated)  
**Auth Required:** Yes  
**Query Parameters:**
- `page` (int, default=1): Page number
- `per_page` (int, default=20, max=100): Items per page
- `search` (string, optional): Search by device name or key
- `is_active` (boolean, optional): Filter by active status

**Response:**
```json
{
  "data": [
    {
      "id": 5,
      "device_key": "M01",
      "name": "Compressor 1",
      "manufacturer": "Siemens",
      "model": "XYZ-500",
      "region": "Zone A",
      "is_active": true,
      "last_seen": "2026-02-19T10:35:00Z",
      "health_score": 85,
      "active_alert_count": 2,
      "current_energy_kw": 12.5
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 15,
    "pages": 1
  }
}
```

---

#### GET /api/v1/devices/{device_id}
**Purpose:** Get device details with parameters  
**Auth Required:** Yes  
**Response:**
```json
{
  "data": {
    "id": 5,
    "device_key": "M01",
    "name": "Compressor 1",
    "manufacturer": "Siemens",
    "is_active": true,
    "last_seen": "2026-02-19T10:35:00Z",
    "parameters": [
      {
        "id": 20,
        "parameter_key": "voltage",
        "display_name": "Voltage",
        "unit": "V",
        "data_type": "float",
        "is_kpi_selected": true
      },
      {
        "id": 21,
        "parameter_key": "current",
        "display_name": "Current",
        "unit": "A",
        "data_type": "float",
        "is_kpi_selected": true
      }
    ]
  }
}
```
**Errors:**
- 404: Device not found (or belongs to different factory)

---

#### POST /api/v1/devices
**Purpose:** Create a new device  
**Auth Required:** Yes  
**Request Body:**
```json
{
  "device_key": "M03",
  "name": "Pump 3",
  "manufacturer": "ABB",
  "model": "P-200",
  "region": "Zone C"
}
```
**Response (201 Created):**
```json
{
  "data": {
    "id": 18,
    "device_key": "M03",
    "name": "Pump 3",
    "api_key": "fk_a8f9d7c6b5e4a3b2c1d0e9f8",
    "is_active": true,
    "created_at": "2026-02-19T10:40:00Z"
  }
}
```
**Errors:**
- 400: Device key already exists

---

#### PATCH /api/v1/devices/{device_id}
**Purpose:** Update device details  
**Auth Required:** Yes  
**Request Body:** (all fields optional)
```json
{
  "name": "Compressor 1 - Updated",
  "region": "Zone A - Building 2",
  "is_active": false
}
```

---

#### DELETE /api/v1/devices/{device_id}
**Purpose:** Soft delete device (sets is_active=false)  
**Auth Required:** Yes  
**Response:** 204 No Content

---

### 5.3 KPI Endpoints

#### GET /api/v1/devices/{device_id}/kpis/live
**Purpose:** Get live KPI values for a device  
**Auth Required:** Yes  
**Response:**
```json
{
  "data": [
    {
      "parameter_key": "voltage",
      "display_name": "Voltage",
      "unit": "V",
      "value": 231.4,
      "is_stale": false,
      "timestamp": "2026-02-19T10:35:12Z"
    },
    {
      "parameter_key": "current",
      "display_name": "Current",
      "unit": "A",
      "value": 3.2,
      "is_stale": false,
      "timestamp": "2026-02-19T10:35:12Z"
    }
  ]
}
```
**Notes:**
- `is_stale=true` if last value > 10 minutes old
- Only returns parameters with `is_kpi_selected=true`

---

#### GET /api/v1/devices/{device_id}/kpis/history
**Purpose:** Get historical KPI data for a parameter  
**Auth Required:** Yes  
**Query Parameters:**
- `parameter` (string, required): Parameter key (e.g., "voltage")
- `start` (ISO datetime, required): Start of time range
- `end` (ISO datetime, required): End of time range
- `interval` (string, optional): Aggregation interval ("1m", "5m", "1h", "1d") - auto-selected if omitted

**Response:**
```json
{
  "data": {
    "parameter": "voltage",
    "interval": "5m",
    "points": [
      {"timestamp": "2026-02-19T10:00:00Z", "value": 230.5},
      {"timestamp": "2026-02-19T10:05:00Z", "value": 231.2},
      {"timestamp": "2026-02-19T10:10:00Z", "value": 232.0}
    ]
  }
}
```

---

#### PATCH /api/v1/devices/{device_id}/parameters/{param_id}
**Purpose:** Update parameter metadata  
**Auth Required:** Yes  
**Request Body:**
```json
{
  "display_name": "Voltage (Line 1)",
  "unit": "V",
  "is_kpi_selected": false
}
```

---

### 5.4 Rule Endpoints

#### GET /api/v1/rules
**Purpose:** List all rules for current factory  
**Auth Required:** Yes  
**Query Parameters:**
- `device_id` (int, optional): Filter by device
- `is_active` (boolean, optional): Filter by active status

**Response:**
```json
{
  "data": [
    {
      "id": 42,
      "name": "High Voltage Alert",
      "description": "Triggers when voltage exceeds safe limits",
      "scope": "device",
      "conditions": {
        "operator": "AND",
        "conditions": [
          {"parameter": "voltage", "operator": "gt", "value": 240}
        ]
      },
      "severity": "critical",
      "cooldown_minutes": 15,
      "is_active": true,
      "schedule_type": "always",
      "notification_channels": {"email": true, "whatsapp": true},
      "device_count": 3,
      "created_at": "2026-02-01T08:00:00Z"
    }
  ]
}
```

---

#### POST /api/v1/rules
**Purpose:** Create a new rule  
**Auth Required:** Yes (requires permission `can_create_rules`)  
**Request Body:**
```json
{
  "name": "Overvoltage Protection",
  "description": "Alert on high voltage",
  "scope": "device",
  "device_ids": [5, 6, 7],
  "conditions": {
    "operator": "OR",
    "conditions": [
      {"parameter": "voltage", "operator": "gt", "value": 240},
      {"parameter": "voltage", "operator": "lt", "value": 200}
    ]
  },
  "severity": "high",
  "cooldown_minutes": 10,
  "schedule_type": "time_window",
  "schedule_config": {
    "start_time": "06:00",
    "end_time": "22:00",
    "days": [1, 2, 3, 4, 5]
  },
  "notification_channels": {"email": true, "whatsapp": false}
}
```

---

#### PATCH /api/v1/rules/{rule_id}
**Purpose:** Update a rule  
**Auth Required:** Yes (requires permission)

---

#### DELETE /api/v1/rules/{rule_id}
**Purpose:** Soft delete rule (sets is_active=false)  
**Auth Required:** Yes  
**Response:** 204 No Content

---

### 5.5 Alert Endpoints

#### GET /api/v1/alerts
**Purpose:** List alerts for current factory  
**Auth Required:** Yes  
**Query Parameters:**
- `device_id` (int, optional): Filter by device
- `severity` (enum, optional): "low", "medium", "high", "critical"
- `resolved` (boolean, optional): Filter by resolution status
- `start` (ISO datetime, optional): Filter by triggered_at >= start
- `end` (ISO datetime, optional): Filter by triggered_at <= end
- `page`, `per_page`: Pagination

**Response:**
```json
{
  "data": [
    {
      "id": 1001,
      "rule_id": 42,
      "rule_name": "High Voltage Alert",
      "device_id": 5,
      "device_name": "Compressor 1",
      "triggered_at": "2026-02-19T10:35:00Z",
      "resolved_at": null,
      "severity": "critical",
      "message": "[High Voltage Alert] voltage (245.2) gt 240",
      "telemetry_snapshot": {"voltage": 245.2, "current": 3.5},
      "notification_sent": true
    }
  ],
  "pagination": {...}
}
```

---

#### GET /api/v1/alerts/{alert_id}
**Purpose:** Get alert details  
**Auth Required:** Yes

---

#### PATCH /api/v1/alerts/{alert_id}/resolve
**Purpose:** Mark alert as resolved  
**Auth Required:** Yes  
**Response:**
```json
{
  "data": {
    "id": 1001,
    "resolved_at": "2026-02-19T11:00:00Z",
    ...
  }
}
```

---

### 5.6 Analytics Endpoints

#### POST /api/v1/analytics/jobs
**Purpose:** Create a new analytics job  
**Auth Required:** Yes (requires permission `can_run_analytics`)  
**Request Body:**
```json
{
  "job_type": "anomaly",
  "mode": "standard",
  "device_ids": [5, 6, 7],
  "date_range_start": "2026-02-12T00:00:00Z",
  "date_range_end": "2026-02-19T00:00:00Z",
  "parameters": {
    "sensitivity": "high",
    "threshold": 2.5
  }
}
```
**Job Types:**
- `anomaly`: Anomaly detection using Isolation Forest
- `failure_prediction`: Predict equipment failures
- `energy_forecast`: Forecast energy consumption using Prophet
- `ai_copilot`: AI-assisted analysis with natural language insights

**Response (201 Created):**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "job_type": "anomaly",
    "status": "pending",
    "created_at": "2026-02-19T10:50:00Z"
  }
}
```

---

#### GET /api/v1/analytics/jobs
**Purpose:** List analytics jobs for current factory  
**Auth Required:** Yes  
**Query Parameters:**
- `status` (enum, optional): "pending", "running", "complete", "failed"

**Response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "job_type": "anomaly",
      "mode": "standard",
      "device_ids": [5, 6, 7],
      "date_range_start": "2026-02-12T00:00:00Z",
      "date_range_end": "2026-02-19T00:00:00Z",
      "status": "complete",
      "result_url": "https://minio:9000/factoryops/1/analytics/550e8400...?X-Amz-Expires=604800",
      "started_at": "2026-02-19T10:50:05Z",
      "completed_at": "2026-02-19T10:52:30Z",
      "created_at": "2026-02-19T10:50:00Z"
    }
  ]
}
```

---

#### GET /api/v1/analytics/jobs/{job_id}
**Purpose:** Get job details and download result  
**Auth Required:** Yes  
**Response:**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "complete",
    "result_url": "https://...",
    "result_preview": {
      "summary": "Detected 12 anomalies across 3 devices",
      "anomalies": [
        {
          "device_id": 5,
          "timestamp": "2026-02-15T14:23:00Z",
          "parameter": "voltage",
          "value": 267.3,
          "score": 0.92,
          "severity": "high"
        }
      ]
    }
  }
}
```

---

### 5.7 Report Endpoints

#### POST /api/v1/reports
**Purpose:** Generate a new report  
**Auth Required:** Yes (requires permission `can_generate_reports`)  
**Request Body:**
```json
{
  "title": "Monthly Production Report - February 2026",
  "device_ids": [5, 6, 7, 8],
  "date_range_start": "2026-02-01T00:00:00Z",
  "date_range_end": "2026-02-28T23:59:59Z",
  "format": "pdf",
  "include_analytics": true,
  "analytics_job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
**Formats:** `pdf`, `excel`, `json`

**Response (201 Created):**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "pending",
    "created_at": "2026-02-19T11:00:00Z"
  }
}
```

---

#### GET /api/v1/reports
**Purpose:** List reports for current factory  
**Auth Required:** Yes

---

#### GET /api/v1/reports/{report_id}
**Purpose:** Get report status  
**Auth Required:** Yes  
**Response:**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "title": "Monthly Production Report - February 2026",
    "format": "pdf",
    "status": "complete",
    "file_url": "https://minio:9000/factoryops/1/reports/7c9e6679...?X-Amz-Expires=86400",
    "file_size_bytes": 1458304,
    "expires_at": "2026-02-20T11:05:00Z",
    "created_at": "2026-02-19T11:00:00Z"
  }
}
```

---

#### GET /api/v1/reports/{report_id}/download
**Purpose:** Download report file  
**Auth Required:** Yes  
**Response:** 302 Redirect to pre-signed MinIO URL

---

### 5.8 User Endpoints (Super Admin Only)

#### GET /api/v1/users
**Purpose:** List users in current factory  
**Auth Required:** Yes (super_admin only)

---

#### POST /api/v1/users/invite
**Purpose:** Invite a new user  
**Auth Required:** Yes (super_admin only)  
**Request Body:**
```json
{
  "email": "newuser@vpc.com",
  "whatsapp_number": "+919876543210",
  "role": "admin",
  "permissions": {
    "can_create_rules": true,
    "can_run_analytics": false,
    "can_generate_reports": true
  }
}
```
**Response:**
```json
{
  "data": {
    "id": 25,
    "email": "newuser@vpc.com",
    "invite_sent": true,
    "invite_token": "kJ8fD3mN9pQ2rS5tU7vX0yZ1aB4cE6gH",
    "invited_at": "2026-02-19T11:10:00Z",
    "invite_link": "http://localhost/accept-invite?token=kJ8fD3mN..."
  }
}
```
**Notes:**
- If SMTP configured: Sends invitation email
- If SMTP not configured: Returns invite_link in response (for manual sharing)
- Token expires in 48 hours

---

#### POST /api/v1/users/accept-invite
**Purpose:** Accept invitation and set password (NO AUTH REQUIRED)  
**Request Body:**
```json
{
  "token": "kJ8fD3mN9pQ2rS5tU7vX0yZ1aB4cE6gH",
  "password": "NewPassword@123"
}
```
**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "user": {...}
}
```
**Notes:**
- Auto-logs in user after accepting invite
- Sets `is_active=true`, clears `invite_token`

---

#### PATCH /api/v1/users/{user_id}/permissions
**Purpose:** Update user permissions  
**Auth Required:** Yes (super_admin only)  
**Request Body:**
```json
{
  "permissions": {
    "can_create_rules": false,
    "can_run_analytics": true,
    "can_generate_reports": true
  }
}
```
**Restrictions:**
- Cannot modify super_admin users
- Cannot modify self

---

#### DELETE /api/v1/users/{user_id}
**Purpose:** Deactivate user (soft delete)  
**Auth Required:** Yes (super_admin only)  
**Restrictions:**
- Cannot delete self
- Cannot delete super_admin users

---

### 5.9 Dashboard & Telemetry Endpoints

#### GET /api/v1/dashboard/summary
**Purpose:** Get dashboard summary statistics  
**Auth Required:** Yes  
**Response:** (see Flow 4.4 for details)

---

#### POST /api/v1/telemetry/ingest
**Purpose:** HTTP-based telemetry ingestion (alternative to MQTT)  
**Auth Required:** Yes (device API key)  
**Request Body:**
```json
{
  "device_key": "M01",
  "metrics": {
    "voltage": 231.4,
    "current": 3.2,
    "power": 745.6
  },
  "timestamp": "2026-02-19T10:35:00Z"
}
```
**Notes:**
- Primarily used for testing
- Production devices should use MQTT for efficiency

---

### 5.10 Observability Endpoints

#### GET /health
**Purpose:** Health check endpoint  
**Auth Required:** No  
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-19T11:15:00Z",
  "dependencies": {
    "mysql": "ok",
    "influxdb": "ok",
    "redis": "ok",
    "minio": "ok"
  }
}
```

---

#### GET /api/v1/metrics
**Purpose:** Prometheus metrics endpoint  
**Auth Required:** No  
**Response:** (Prometheus text format)
```
# HELP factoryops_telemetry_messages_total Total telemetry messages processed
# TYPE factoryops_telemetry_messages_total counter
factoryops_telemetry_messages_total{factory_id="1"} 45678

# HELP factoryops_alerts_triggered_total Total alerts triggered
# TYPE factoryops_alerts_triggered_total counter
factoryops_alerts_triggered_total{factory_id="1",severity="critical"} 23
factoryops_alerts_triggered_total{factory_id="1",severity="high"} 145

# HELP factoryops_api_request_duration_seconds API request duration
# TYPE factoryops_api_request_duration_seconds histogram
factoryops_api_request_duration_seconds_bucket{method="GET",endpoint="/devices",status_code="200",le="0.1"} 1234
...
```

---

### 5.11 Error Response Format

All error responses follow this structure:
```json
{
  "detail": "Human-readable error message"
}
```

**Common HTTP Status Codes:**
- 200: Success
- 201: Created
- 204: No Content (successful deletion)
- 400: Bad Request (validation error)
- 401: Unauthorized (missing/invalid token)
- 403: Forbidden (insufficient permissions)
- 404: Not Found (resource doesn't exist or belongs to different factory)
- 422: Unprocessable Entity (Pydantic validation error)
- 500: Internal Server Error

---


## 6. Multi-Tenancy & Security

### 6.1 Factory Isolation Architecture

**Core Principle:** Every resource belongs to exactly ONE factory. Cross-factory access is strictly forbidden.

#### How Factory Isolation Works

1. **JWT Token Structure**
   ```json
   {
     "sub": "user@example.com",
     "user_id": 123,
     "factory_id": "f7c8d9e0-1234-5678-90ab-cdef12345678",
     "role": "admin",
     "exp": 1234567890
   }
   ```

2. **Enforcement Points**

   | Layer | Enforcement Mechanism |
   |-------|----------------------|
   | API Routes | `get_current_user()` dependency extracts `factory_id` from JWT |
   | Repository Layer | ALL queries include `WHERE factory_id = :factory_id` |
   | InfluxDB Queries | ALL queries include `|> filter(fn: (r) => r["factory_id"] == "{factory_id}")` |
   | Celery Tasks | Tasks receive and validate `factory_id` parameter |
   | MQTT Topics | Topic structure: `factories/{factory_key}/devices/{device_key}/telemetry` |

3. **Database Enforcement**

   **Every MySQL table** (except `factories` and system tables) has:
   - `factory_id` column (UUID, NOT NULL)
   - Composite unique constraints including `factory_id`
   - Foreign key: `FOREIGN KEY (factory_id) REFERENCES factories(id) ON DELETE CASCADE`

   Example from `devices` table:
   ```sql
   CREATE TABLE devices (
       id INT AUTO_INCREMENT PRIMARY KEY,
       factory_id CHAR(36) NOT NULL,
       device_key VARCHAR(50) NOT NULL,
       name VARCHAR(255) NOT NULL,
       FOREIGN KEY (factory_id) REFERENCES factories(id) ON DELETE CASCADE,
       UNIQUE KEY unique_device_per_factory (factory_id, device_key)
   );
   ```

4. **Repository Pattern Example**

   From `backend/app/repositories/device_repo.py`:
   ```python
   async def get_by_id(db: AsyncSession, factory_id: str, device_id: int) -> Device | None:
       result = await db.execute(
           select(Device).where(
               Device.factory_id == factory_id,  # ← CRITICAL: Always filter by factory_id
               Device.id == device_id
           )
       )
       return result.scalar_one_or_none()
   ```

   **What happens if factory_id is wrong?** → Returns `None` → API returns 404 "Not Found"
   
   **Why 404 instead of 403?** → Security: Don't reveal that the resource exists in another factory

### 6.2 Authentication Flow

**Step-by-Step Login Process:**

1. **User submits credentials** → `POST /api/v1/auth/login`
   ```json
   {
     "email": "admin@vpc.com",
     "password": "Admin@123"
   }
   ```

2. **API verifies password** → `security.verify_password(plain_password, user.hashed_password)`

3. **JWT token created** → Includes `factory_id` from user's record
   ```python
   from backend/app/core/security.py:
   
   def create_access_token(data: dict) -> str:
       to_encode = data.copy()
       expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
       to_encode.update({"exp": expire})
       return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
   ```

4. **Client stores token** → localStorage in browser

5. **All subsequent requests** → Include `Authorization: Bearer <token>` header

6. **API validates token** → `get_current_user()` dependency:
   ```python
   from backend/app/core/dependencies.py:
   
   async def get_current_user(
       token: str = Depends(oauth2_scheme),
       db: AsyncSession = Depends(get_db)
   ) -> User:
       try:
           payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
           email: str = payload.get("sub")
           factory_id: str = payload.get("factory_id")  # ← Extracted here
       except JWTError:
           raise HTTPException(status_code=401, detail="Invalid authentication")
       
       user = await user_repo.get_by_email(db, factory_id, email)
       if not user or not user.is_active:
           raise HTTPException(status_code=401, detail="User not found or inactive")
       
       return user  # ← user.factory_id is now available
   ```

### 6.3 Authorization & Permissions

**Role-Based Access Control (RBAC):**

| Role | Capabilities |
|------|-------------|
| `super_admin` | Full access: manage users, devices, rules, analytics, reports |
| `admin` | Manage devices, rules; view analytics and reports |
| `viewer` | Read-only access to dashboards and KPIs |
| `operator` | Acknowledge alerts, view devices, cannot modify rules |

**Permission Structure:**

Stored in `users.permissions` JSON column:
```json
{
  "can_create_rules": true,
  "can_run_analytics": true,
  "can_generate_reports": false
}
```

**Permission Check Pattern:**
```python
def require_permission(permission_key: str):
    def permission_checker(user: User = Depends(get_current_user)):
        if user.role == "super_admin":
            return user  # Super admin bypasses permission checks
        
        if not user.permissions.get(permission_key, False):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        return user
    return permission_checker

# Usage in route:
@router.post("/rules", dependencies=[Depends(require_permission("can_create_rules"))])
async def create_rule(...):
    ...
```

### 6.4 What a Malicious User CANNOT Do

**Scenario 1: Cross-Factory Data Access**

❌ **Attack:** User from Factory A tries to access Factory B's device:
```bash
# Factory A user has factory_id="factory-a-uuid" in JWT
GET /api/v1/devices/999  # Device 999 belongs to Factory B
```

**Defense:**
1. JWT is valid → user authenticated ✓
2. API calls `device_repo.get_by_id(db, factory_id="factory-a-uuid", device_id=999)`
3. SQL: `SELECT * FROM devices WHERE factory_id='factory-a-uuid' AND id=999`
4. No match found → Returns `None`
5. API returns `404 Not Found` (doesn't reveal device exists elsewhere)

**Result:** ✅ Attack blocked at repository layer

---

**Scenario 2: JWT Token Manipulation**

❌ **Attack:** User modifies JWT to change `factory_id`:
```javascript
// Original token payload
{
  "factory_id": "factory-a-uuid",
  "user_id": 123,
  "exp": 1234567890
}

// Attacker tries to change factory_id
{
  "factory_id": "factory-b-uuid",  // ← Modified
  "user_id": 123,
  "exp": 1234567890
}
```

**Defense:**
1. JWT is signed with `SECRET_KEY` (256-bit random string in production)
2. Any modification invalidates the signature
3. `jwt.decode()` raises `JWTError`
4. API returns `401 Unauthorized`

**Result:** ✅ Attack blocked at authentication layer

---

**Scenario 3: SQL Injection**

❌ **Attack:** User tries SQL injection in device name:
```json
POST /api/v1/devices
{
  "name": "'; DROP TABLE devices; --",
  "device_key": "M01"
}
```

**Defense:**
1. SQLAlchemy ORM uses parameterized queries
2. Input is treated as data, not executable SQL
3. Device created with literal name: `'; DROP TABLE devices; --`

**Result:** ✅ Attack blocked by ORM parameterization

---

**Scenario 4: Bypassing API with Direct Database Access**

❌ **Attack:** Attacker gains MySQL access and modifies data directly

**Defense:**
1. MySQL port (3306) NOT exposed publicly (only internal Docker network)
2. Strong password required (from Docker secrets in production)
3. Database backups encrypted and versioned
4. Audit logs track all data changes

**Result:** ✅ Multiple layers of defense

---

**Scenario 5: MQTT Message Spoofing**

❌ **Attack:** Attacker publishes fake telemetry to another factory's topic:
```bash
mosquitto_pub -h mqtt-broker -p 1883 \
  -t "factories/victim-factory/devices/M01/telemetry" \
  -m '{"metrics":{"voltage":999999}}'
```

**Defense:**
1. Telemetry service validates `factory_key` exists in database
2. Validates `device_key` belongs to that factory
3. If validation fails → message rejected (not written to InfluxDB)
4. Production: MQTT broker requires authentication (username/password per factory)

**Result:** ✅ Attack blocked at ingestion validation layer

### 6.5 Security Best Practices Implemented

| Practice | Implementation |
|----------|---------------|
| **Password Hashing** | bcrypt with salt (via `passlib`) |
| **Token Expiry** | JWT expires after 60 minutes (configurable) |
| **HTTPS Enforcement** | NGINX redirects HTTP → HTTPS in production |
| **CORS Protection** | FastAPI CORS middleware with explicit origins |
| **Rate Limiting** | NGINX: 100 req/min per IP on `/api/*` |
| **Input Validation** | Pydantic schemas validate all request bodies |
| **SQL Injection Prevention** | SQLAlchemy ORM with parameterized queries |
| **Secret Management** | Docker secrets (production) + `.env` (dev) |
| **Audit Logging** | Structured JSON logs with `factory_id`, `user_id` |
| **Security Headers** | HSTS, CSP, X-Frame-Options, X-Content-Type-Options |


## 7. Frontend Structure

### 7.1 Technology Stack

- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite 5
- **Styling:** TailwindCSS 3
- **Charts:** Recharts 2.15
- **State Management:** Zustand (authStore, uiStore)
- **HTTP Client:** Axios
- **Routing:** React Router 6

### 7.2 Directory Structure

```
frontend/src/
├── api/
│   ├── client.ts          # Axios instance with auth interceptor
│   └── endpoints.ts       # API endpoint definitions
├── components/
│   ├── charts/
│   │   └── TelemetryChart.tsx
│   ├── kpi/
│   │   ├── KPICard.tsx
│   │   └── KPICardGrid.tsx
│   ├── rules/
│   │   ├── ConditionGroupEditor.tsx
│   │   └── ConditionLeafEditor.tsx
│   └── ui/
│       ├── MainLayout.tsx
│       └── Sidebar.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useDevices.ts
│   ├── useKPIs.ts
│   ├── useRules.ts
│   ├── useAlerts.ts
│   ├── useAnalytics.ts
│   ├── useReports.ts
│   └── useUsers.ts
├── pages/
│   ├── Login.tsx
│   ├── FactorySelect.tsx
│   ├── Dashboard.tsx
│   ├── Machines.tsx
│   ├── DeviceDetail.tsx
│   ├── Rules.tsx
│   ├── RuleBuilder.tsx
│   ├── Analytics.tsx
│   ├── Reports.tsx
│   └── Users.tsx
├── stores/
│   ├── authStore.ts       # User, token, factory state
│   └── uiStore.ts         # UI state (sidebar open, etc.)
├── types/
│   └── index.ts           # TypeScript interfaces
├── App.tsx                # Root component with routing
└── main.tsx               # Entry point
```

### 7.3 Page-by-Page Breakdown

#### 7.3.1 Login Flow (`Login.tsx` → `FactorySelect.tsx` → `Dashboard.tsx`)

**Login.tsx**
- **Purpose:** Authenticate user with email/password
- **API Calls:**
  - `POST /api/v1/auth/login` → Receives JWT token
- **Success Flow:**
  1. Store token in authStore
  2. Redirect to `/factory-select`
- **UI Elements:**
  - Email input
  - Password input (masked)
  - "Login" button
  - Error message display

**FactorySelect.tsx**
- **Purpose:** User selects which factory to manage (for multi-factory users)
- **API Calls:**
  - `GET /api/v1/auth/me` → Get current user's factory
- **Success Flow:**
  1. Extract `factory_id` from user
  2. Store in authStore
  3. Redirect to `/dashboard`
- **UI Elements:**
  - Factory logo/name
  - "Continue" button

**Dashboard.tsx**
- **Purpose:** Overview of factory health and key metrics
- **API Calls:**
  - `GET /api/v1/dashboard/summary` → Total devices, alerts (24h), active rules
  - `GET /api/v1/devices` → Device list
  - `GET /api/v1/alerts?limit=5` → Recent alerts
- **Polling:** Refreshes every 30 seconds
- **UI Components:**
  - Summary cards (Device count, Alert count, Active rules)
  - Device status table
  - Recent alerts list
  - Quick actions (New Rule, View Analytics)

#### 7.3.2 Device Management

**Machines.tsx**
- **Purpose:** List all devices with live status
- **API Calls:**
  - `GET /api/v1/devices` → All devices
  - `GET /api/v1/devices/{id}/kpis/live` (for each device) → Live KPI values
- **Polling:** KPIs refresh every 5 seconds
- **UI Features:**
  - Searchable device table
  - Status badges (Online: green, Offline: gray, Warning: yellow)
  - "Add Device" button
  - Click row → Navigate to `/devices/{id}`

**DeviceDetail.tsx**
- **Purpose:** Deep dive into single device with charts
- **Route:** `/devices/:id`
- **API Calls:**
  - `GET /api/v1/devices/{id}` → Device metadata
  - `GET /api/v1/devices/{id}/parameters` → Available parameters
  - `GET /api/v1/devices/{id}/kpis/live` → Current values
  - `GET /api/v1/devices/{id}/kpis/history?start=...&end=...` → Historical data
- **Polling:** Live KPIs every 5 seconds
- **UI Features:**
  - Device info card (Name, Type, Status, Last seen)
  - KPI cards grid (Voltage, Current, Power, etc.)
  - Time-series chart (Recharts LineChart)
    - User can select parameters to display
    - Time range selector (1h, 6h, 24h, 7d)
  - Parameter management table
    - Toggle `is_kpi_selected` checkbox
    - Configure min/max thresholds

**Code Example - KPI Chart Component:**
```typescript
// From DeviceDetail.tsx
<ResponsiveContainer width="100%" height={300}>
  <LineChart data={historyData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="timestamp" />
    <YAxis />
    <Tooltip />
    <Legend />
    {selectedParams.map(param => (
      <Line
        key={param}
        type="monotone"
        dataKey={param}
        stroke={getColorForParam(param)}
        strokeWidth={2}
      />
    ))}
  </LineChart>
</ResponsiveContainer>
```

#### 7.3.3 Rules & Alerts

**Rules.tsx**
- **Purpose:** List and manage alert rules
- **API Calls:**
  - `GET /api/v1/rules` → All rules for factory
  - `PATCH /api/v1/rules/{id}` → Toggle `is_active`
  - `DELETE /api/v1/rules/{id}` → Delete rule
- **UI Features:**
  - Rule table with columns:
    - Name
    - Condition (formatted, e.g., "voltage > 240")
    - Severity badge
    - Active toggle switch
    - Last triggered timestamp
  - "Create Rule" button → Navigate to `/rules/builder`
  - Actions: Edit, Delete (with confirmation)

**RuleBuilder.tsx**
- **Purpose:** Visual rule builder with condition tree
- **Route:** `/rules/builder` (create) or `/rules/:id/edit`
- **API Calls:**
  - `GET /api/v1/devices` → Device selector
  - `GET /api/v1/devices/{id}/parameters` → Parameter list
  - `POST /api/v1/rules` → Create rule
  - `PATCH /api/v1/rules/{id}` → Update rule
- **UI Components:**
  - Rule name input
  - Device selector (multi-select)
  - Condition builder (nested AND/OR groups)
    - `ConditionGroupEditor` component (recursive)
    - `ConditionLeafEditor` component (parameter, operator, value)
  - Severity selector (low, medium, high, critical)
  - Cooldown duration input
  - Notification settings (Email, WhatsApp)
  - "Save Rule" button

**Condition Builder Example:**
```typescript
// Rule condition structure
{
  "type": "and",
  "conditions": [
    {
      "type": "leaf",
      "parameter": "voltage",
      "operator": ">",
      "value": 240
    },
    {
      "type": "or",
      "conditions": [
        {
          "type": "leaf",
          "parameter": "current",
          "operator": ">",
          "value": 5
        },
        {
          "type": "leaf",
          "parameter": "temperature",
          "operator": ">",
          "value": 80
        }
      ]
    }
  ]
}
```

**Visual Representation:**
```
AND
├── voltage > 240
└── OR
    ├── current > 5
    └── temperature > 80
```

#### 7.3.4 Analytics & Reports

**Analytics.tsx**
- **Purpose:** Create and manage predictive analytics jobs
- **API Calls:**
  - `GET /api/v1/analytics/jobs` → All jobs
  - `POST /api/v1/analytics/jobs` → Create new job
  - `GET /api/v1/analytics/jobs/{id}` → Poll for status
  - Download presigned URL → Fetch results JSON
- **Polling:** Jobs with status `running` polled every 3 seconds
- **UI Features:**
  - Job list table (ID, Type, Status, Created, Actions)
  - Status badges:
    - Pending: yellow
    - Running: blue (with spinner)
    - Complete: green
    - Failed: red
  - "New Analysis" button → Modal:
    - Mode selector (Standard / AI Co-Pilot)
    - Device multi-select
    - Date range picker
    - Analysis type (Anomaly Detection / Forecasting)
    - Submit → Job created with status `pending`
  - Expandable rows for complete jobs:
    - Summary text
    - Anomaly list (if type=anomaly)
    - Forecast chart (if type=forecast):
      ```tsx
      <AreaChart data={forecast}>
        <Area type="monotone" dataKey="yhat" stroke="#2563eb" fill="#3b82f680" />
        <Area type="monotone" dataKey="yhat_lower" stroke="#9ca3af" fill="none" />
        <Area type="monotone" dataKey="yhat_upper" stroke="#9ca3af" fill="none" />
      </AreaChart>
      ```
    - Download button → Opens presigned URL

**Reports.tsx**
- **Purpose:** Generate PDF/Excel/JSON reports
- **API Calls:**
  - `GET /api/v1/reports` → All reports
  - `POST /api/v1/reports` → Create new report
  - `GET /api/v1/reports/{id}` → Poll for status
  - `GET /api/v1/reports/{id}/download` → Get presigned URL (redirect)
- **Polling:** Reports with status `running` polled every 5 seconds
- **UI Features:**
  - Report list table (Title, Format, Status, Created, Size, Actions)
  - "Generate Report" button → Modal:
    - Title input
    - Device multi-select (searchable)
    - Date range picker (start/end)
    - Format radio buttons (PDF / Excel / JSON)
    - Include Analytics toggle → Shows job selector if enabled
    - Submit → Report created with status `pending`
  - Download button (enabled when status=`complete`)
    - Opens presigned URL in new tab
    - PDF auto-downloads
    - Excel auto-downloads
    - JSON displays in browser

#### 7.3.5 User Management (Super Admin Only)

**Users.tsx**
- **Purpose:** Invite and manage factory users
- **Route:** `/users`
- **Auth:** Requires `super_admin` role
- **API Calls:**
  - `GET /api/v1/users` → All factory users
  - `POST /api/v1/users/invite` → Send invite email
  - `PATCH /api/v1/users/{id}/permissions` → Update permissions
  - `DELETE /api/v1/users/{id}` → Deactivate user
- **UI Features:**
  - User table:
    - Email
    - Role badge
    - Permission chips (Create Rules, Run Analytics, etc.)
    - Status (Active / Inactive)
    - Last login timestamp
  - "Invite Admin" button → Modal:
    - Email input
    - WhatsApp number input (optional)
    - Permission toggles:
      - Can Create Rules
      - Can Run Analytics
      - Can Generate Reports
    - Submit → Invite email sent with token link
  - Per-row actions:
    - Edit permissions → Inline drawer with toggles
    - Deactivate → Confirmation dialog → Soft delete

### 7.4 State Management

#### authStore (Zustand)

**Location:** `frontend/src/stores/authStore.ts`

**State Shape:**
```typescript
interface AuthState {
  token: string | null;
  user: User | null;
  factory: Factory | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setFactory: (factory: Factory) => void;
}
```

**Key Methods:**

```typescript
// Login - called from Login.tsx
const login = async (email: string, password: string) => {
  const response = await axios.post('/api/v1/auth/login', { email, password });
  const { access_token, user } = response.data;
  
  set({
    token: access_token,
    user: user,
    isAuthenticated: true
  });
  
  localStorage.setItem('token', access_token);
};

// Logout - clears all state
const logout = () => {
  set({
    token: null,
    user: null,
    factory: null,
    isAuthenticated: false
  });
  
  localStorage.removeItem('token');
  window.location.href = '/login';
};
```

#### uiStore (Zustand)

**Location:** `frontend/src/stores/uiStore.ts`

**State Shape:**
```typescript
interface UIState {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  currentPage: string;
  setCurrentPage: (page: string) => void;
}
```

### 7.5 Custom Hooks

All hooks follow a consistent pattern: fetch data, handle loading/error states, provide mutation functions.

**Example: useDevices.ts**

```typescript
export const useDevices = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const response = await api.get('/devices');
      setDevices(response.data.devices);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createDevice = async (data: CreateDeviceRequest) => {
    const response = await api.post('/devices', data);
    setDevices([...devices, response.data]);
    return response.data;
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  return { devices, loading, error, createDevice, refetch: fetchDevices };
};
```

**Available Hooks:**

| Hook | Purpose | Key Methods |
|------|---------|-------------|
| `useAuth` | Authentication state | `login()`, `logout()`, `checkAuth()` |
| `useDevices` | Device CRUD | `createDevice()`, `updateDevice()`, `deleteDevice()` |
| `useKPIs` | KPI data fetching | `fetchLiveKPIs()`, `fetchHistoricalKPIs()` |
| `useRules` | Rule management | `createRule()`, `updateRule()`, `toggleActive()` |
| `useAlerts` | Alert list | `fetchAlerts()`, `acknowledgeAlert()` |
| `useAnalytics` | Analytics jobs | `createJob()`, `pollJob()`, `fetchResults()` |
| `useReports` | Report generation | `createReport()`, `pollReport()`, `downloadReport()` |
| `useUsers` | User management | `inviteUser()`, `updatePermissions()`, `deactivate()` |

### 7.6 API Client Configuration

**Location:** `frontend/src/api/client.ts`

```typescript
import axios from 'axios';
import { useAuthStore } from '../stores/authStore';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
});

// Request interceptor - adds auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handles 401 (token expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 7.7 Component Hierarchy

**Visual Tree:**
```
App.tsx
├── MainLayout.tsx (authenticated routes only)
│   ├── Sidebar.tsx
│   │   ├── Logo
│   │   └── Navigation Links
│   │       ├── Dashboard
│   │       ├── Machines
│   │       ├── Rules
│   │       ├── Analytics
│   │       ├── Reports
│   │       └── Users (super_admin only)
│   └── <Page Content>
│       ├── Dashboard.tsx
│       │   ├── Summary Cards
│       │   ├── Device Status Table
│       │   └── Recent Alerts
│       ├── Machines.tsx
│       │   ├── Search Bar
│       │   ├── Device Table
│       │   └── KPICardGrid (per device)
│       ├── DeviceDetail.tsx
│       │   ├── Device Info Card
│       │   ├── KPICardGrid
│       │   ├── TelemetryChart
│       │   └── Parameter Table
│       ├── Rules.tsx
│       │   └── Rule Table
│       ├── RuleBuilder.tsx
│       │   ├── ConditionGroupEditor (recursive)
│       │   │   └── ConditionLeafEditor
│       │   └── Notification Settings
│       ├── Analytics.tsx
│       │   ├── Job Table
│       │   └── Results Panel
│       │       └── AreaChart (for forecasts)
│       ├── Reports.tsx
│       │   └── Report Table
│       └── Users.tsx
│           └── User Table
└── Unauthenticated Routes
    ├── Login.tsx
    └── FactorySelect.tsx
```

### 7.8 Styling Patterns

**TailwindCSS Utility Classes:**

Common patterns used throughout:

```tsx
// Card container
<div className="bg-white rounded-lg shadow-md p-6">

// Primary button
<button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">

// Status badge (green)
<span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">

// Table row
<tr className="border-b hover:bg-gray-50">

// Grid layout (4 columns)
<div className="grid grid-cols-4 gap-4">
```

**Responsive Design:**

All pages are mobile-responsive:
```tsx
// Example from Dashboard.tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* Mobile: 1 column, Tablet: 2 columns, Desktop: 4 columns */}
</div>
```


## 8. How To Run & Debug

### 8.1 Prerequisites

**Required Software:**

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Git | 2.30+ | Version control |
| Node.js | 18+ | Frontend development (optional) |
| Python | 3.11+ | Backend development (optional) |

**System Requirements:**

- **RAM:** 8GB minimum, 16GB recommended
- **CPU:** 4 cores minimum
- **Disk:** 20GB free space (for images + data)
- **OS:** macOS, Linux, or Windows with WSL2

### 8.2 First-Time Setup

**Step 1: Clone Repository**

```bash
git clone https://github.com/your-org/factoryops.git
cd factoryops
```

**Step 2: Create Environment File**

```bash
cp .env.example .env
```

**Step 3: Review and Edit `.env`**

```bash
# Open in your editor
nano .env  # or vim, code, etc.
```

**Critical Variables to Set:**

```bash
# Database
MYSQL_ROOT_PASSWORD=<generate-strong-password>
MYSQL_USER=factoryops
MYSQL_PASSWORD=<generate-strong-password>
MYSQL_DATABASE=factoryops_db

# Security (MUST CHANGE IN PRODUCTION!)
SECRET_KEY=<generate-256-bit-random-string>
# Generate with: openssl rand -hex 32

# InfluxDB
INFLUXDB_TOKEN=<generate-influxdb-token>
# Generate with: openssl rand -base64 32

# MinIO (S3-compatible storage)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<generate-strong-password>

# SMTP (for email notifications) - OPTIONAL for dev
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=<app-specific-password>

# Twilio (for WhatsApp notifications) - OPTIONAL
TWILIO_ACCOUNT_SID=<your-twilio-sid>
TWILIO_AUTH_TOKEN=<your-twilio-token>
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

**Step 4: Start All Services**

```bash
cd docker
docker compose up -d
```

**Expected Output:**
```
[+] Running 11/11
 ✔ Network factoryops_default       Created
 ✔ Container factoryops-mysql       Started
 ✔ Container factoryops-redis       Started
 ✔ Container factoryops-influxdb    Started
 ✔ Container factoryops-minio       Started
 ✔ Container factoryops-mqtt        Started
 ✔ Container factoryops-api         Started
 ✔ Container factoryops-telemetry   Started
 ✔ Container factoryops-worker      Started
 ✔ Container factoryops-frontend    Started
 ✔ Container factoryops-nginx       Started
```

**Step 5: Wait for Services to Initialize**

```bash
# Check all services are healthy
docker compose ps

# Expected: all services in "healthy" state
# This may take 30-60 seconds
```

**Step 6: Run Database Migrations**

```bash
docker compose exec api alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade -> 41d31b3cb96e, initial schema
```

**Step 7: Seed Initial Data**

```bash
docker compose exec api python scripts/seed.py
```

**Expected Output:**
```
✓ Factory 'VPC Engineering' created
✓ Super admin user created: admin@vpc.com
✓ Admin user created: manager@vpc.com
✓ Device 'Machine M01' created
✓ Device 'Machine M02' created
✓ Sample rule created
✓ Seed complete!
```

**Step 8: Verify System is Running**

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2026-02-19T12:34:56.789Z",
  "dependencies": {
    "database": "ok",
    "redis": "ok",
    "influxdb": "ok",
    "minio": "ok"
  }
}
```

**Step 9: Access Frontend**

Open browser: **http://localhost:3000**

**Default Login Credentials:**

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@vpc.com | Admin@123 |
| Admin | manager@vpc.com | Manager@123 |

### 8.3 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | React application |
| API (direct) | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger UI |
| InfluxDB UI | http://localhost:8086 | InfluxDB admin |
| MinIO Console | http://localhost:9001 | Object storage UI |
| MQTT Broker | localhost:1883 | Telemetry ingestion |

### 8.4 Start/Stop Commands

**Start All Services:**
```bash
cd docker
docker compose up -d
```

**Stop All Services:**
```bash
docker compose down
```

**Stop and Remove All Data (DESTRUCTIVE!):**
```bash
docker compose down -v
# -v flag removes all volumes (database data will be lost)
```

**Restart Single Service:**
```bash
docker compose restart api
docker compose restart telemetry
docker compose restart worker
```

**Rebuild After Code Changes:**
```bash
# Rebuild specific service
docker compose build api
docker compose up -d api

# Rebuild all services
docker compose build
docker compose up -d
```

### 8.5 Viewing Logs

**All Services:**
```bash
docker compose logs -f
```

**Specific Service:**
```bash
docker compose logs -f api
docker compose logs -f telemetry
docker compose logs -f worker
```

**Last N Lines:**
```bash
docker compose logs --tail=100 api
```

**Follow New Logs Only:**
```bash
docker compose logs -f --since=5m api
# Shows logs from last 5 minutes
```

**Search Logs:**
```bash
docker compose logs api | grep "factory_id"
docker compose logs telemetry | grep "ERROR"
```

**Log Format (JSON Structured):**
```json
{
  "event": "device.created",
  "timestamp": "2026-02-19T12:34:56.789Z",
  "level": "info",
  "factory_id": "f7c8d9e0-1234-5678-90ab-cdef12345678",
  "device_id": 123,
  "device_key": "M01",
  "user_id": 1
}
```

### 8.6 Common Errors & Solutions

#### Error 1: Port Already in Use

**Symptom:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:3000: bind: address already in use
```

**Cause:** Another process is using port 3000, 8000, 3306, etc.

**Solution:**
```bash
# Find process using port 3000
lsof -i :3000  # macOS/Linux
netstat -ano | findstr :3000  # Windows

# Kill the process or change port in docker-compose.yml
```

#### Error 2: Database Connection Failed

**Symptom:**
```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server")
```

**Cause:** MySQL container not ready yet

**Solution:**
```bash
# Wait 30 seconds and try again
docker compose ps mysql

# Check MySQL logs
docker compose logs mysql | tail -50

# Verify MySQL is healthy
docker compose exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SELECT 1"
```

#### Error 3: InfluxDB Token Invalid

**Symptom:**
```
influxdb_client.rest.ApiException: (401) Unauthorized
```

**Cause:** `INFLUXDB_TOKEN` in `.env` doesn't match actual token

**Solution:**
```bash
# Get InfluxDB setup status
docker compose exec influxdb influx auth list

# Regenerate token
docker compose exec influxdb influx auth create \
  --org factoryops \
  --all-access

# Update .env with new token and restart services
docker compose restart api telemetry
```

#### Error 4: MQTT Connection Refused

**Symptom:**
```
paho.mqtt.client.WebsocketConnectionError: [Errno 111] Connection refused
```

**Cause:** MQTT broker (Mosquitto) not running

**Solution:**
```bash
# Check MQTT broker status
docker compose ps mqtt

# Restart MQTT broker
docker compose restart mqtt

# Test connection manually
mosquitto_pub -h localhost -p 1883 -t "test/topic" -m "hello"
```

#### Error 5: Frontend Shows "Network Error"

**Symptom:** Browser console shows `ERR_CONNECTION_REFUSED`

**Cause:** API service not running or CORS misconfigured

**Solution:**
```bash
# Check API is running
docker compose ps api

# Check API logs for errors
docker compose logs api | tail -50

# Verify API responds
curl http://localhost:8000/health

# Check CORS settings in backend/app/main.py
# Ensure VITE_API_BASE_URL in .env matches API URL
```

#### Error 6: Migrations Fail

**Symptom:**
```
alembic.util.exc.CommandError: Target database is not up to date.
```

**Cause:** Database schema out of sync

**Solution:**
```bash
# Check current migration version
docker compose exec api alembic current

# View migration history
docker compose exec api alembic history

# Force upgrade to latest
docker compose exec api alembic upgrade head

# If completely broken, recreate database (DESTRUCTIVE!)
docker compose down -v
docker compose up -d mysql
# Wait 30 seconds
docker compose up -d api
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed.py
```

#### Error 7: Celery Worker Not Processing Tasks

**Symptom:** Analytics jobs stay in `pending` status forever

**Cause:** Celery worker crashed or not running

**Solution:**
```bash
# Check worker status
docker compose ps worker

# Check worker logs
docker compose logs worker | tail -100

# Common issue: Redis connection
docker compose exec worker redis-cli -h redis ping
# Expected: PONG

# Restart worker
docker compose restart worker

# Monitor worker in real-time
docker compose logs -f worker
```

#### Error 8: "Permission Denied" in Docker

**Symptom:**
```
Got permission denied while trying to connect to the Docker daemon socket
```

**Cause:** User not in `docker` group (Linux)

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, then:
docker compose ps
# Should work without sudo
```

### 8.7 Debugging Workflows

#### Debug Workflow 1: Trace a Telemetry Message

**Goal:** Understand why telemetry isn't appearing in dashboard

**Steps:**

1. **Publish test message:**
   ```bash
   mosquitto_pub -h localhost -p 1883 \
     -t "factories/vpc/devices/M01/telemetry" \
     -m '{"metrics":{"voltage":231.5,"current":3.2}}'
   ```

2. **Check MQTT broker received it:**
   ```bash
   docker compose logs mqtt | grep "M01"
   ```

3. **Check telemetry service processed it:**
   ```bash
   docker compose logs telemetry | grep "telemetry.processed"
   # Look for: factory_id, device_id, metric_count
   ```

4. **Check InfluxDB has data:**
   ```bash
   docker compose exec influxdb influx query '
     from(bucket: "factoryops")
       |> range(start: -1h)
       |> filter(fn: (r) => r["device_key"] == "M01")
   '
   ```

5. **Check MySQL device_parameters table:**
   ```bash
   docker compose exec mysql mysql -u factoryops -p${MYSQL_PASSWORD} factoryops_db -e "
     SELECT parameter_key, data_type, discovered_at
     FROM device_parameters
     WHERE device_id = (SELECT id FROM devices WHERE device_key = 'M01')
   "
   ```

6. **Test API endpoint:**
   ```bash
   # Login first to get token
   TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@vpc.com","password":"Admin@123"}' \
     | jq -r '.access_token')

   # Get device ID
   DEVICE_ID=$(curl http://localhost:8000/api/v1/devices \
     -H "Authorization: Bearer $TOKEN" \
     | jq -r '.devices[] | select(.device_key=="M01") | .id')

   # Fetch live KPIs
   curl http://localhost:8000/api/v1/devices/$DEVICE_ID/kpis/live \
     -H "Authorization: Bearer $TOKEN" | jq
   ```

#### Debug Workflow 2: Trace an Alert

**Goal:** Understand why rule didn't trigger alert

**Steps:**

1. **Verify rule exists and is active:**
   ```bash
   docker compose exec mysql mysql -u factoryops -p${MYSQL_PASSWORD} factoryops_db -e "
     SELECT id, name, is_active, condition, severity
     FROM rules
     WHERE is_active = 1
   "
   ```

2. **Publish telemetry that should trigger rule:**
   ```bash
   mosquitto_pub -h localhost -p 1883 \
     -t "factories/vpc/devices/M01/telemetry" \
     -m '{"metrics":{"voltage":999}}'  # Extreme value to trigger
   ```

3. **Check if rule evaluation task was queued:**
   ```bash
   docker compose logs worker | grep "evaluate_rules_task"
   ```

4. **Check Redis queue:**
   ```bash
   docker compose exec redis redis-cli LLEN celery
   # Non-zero = tasks waiting
   ```

5. **Check alert was created:**
   ```bash
   docker compose exec mysql mysql -u factoryops -p${MYSQL_PASSWORD} factoryops_db -e "
     SELECT id, rule_id, device_id, message, severity, triggered_at
     FROM alerts
     ORDER BY triggered_at DESC
     LIMIT 5
   "
   ```

6. **Check notification was sent:**
   ```bash
   docker compose logs worker | grep "notification.email_sent"
   ```

#### Debug Workflow 3: Frontend Not Loading Data

**Goal:** Diagnose API communication issues

**Steps:**

1. **Open browser DevTools (F12) → Network tab**

2. **Refresh page and check failed requests:**
   - Red status codes (401, 403, 404, 500)
   - Note the endpoint and status

3. **Check CORS errors in Console:**
   ```
   Access to XMLHttpRequest at 'http://localhost:8000/api/v1/devices'
   from origin 'http://localhost:3000' has been blocked by CORS policy
   ```

   **Solution:** Verify `backend/app/main.py` has:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],  # ← Must match frontend URL
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

4. **Check token validity:**
   ```javascript
   // In browser console
   localStorage.getItem('token')
   // Copy token, go to jwt.io and decode
   // Check 'exp' (expiry) is in the future
   ```

5. **Test API directly with curl:**
   ```bash
   curl http://localhost:8000/api/v1/devices \
     -H "Authorization: Bearer <paste-token-here>"
   ```

### 8.8 Development Mode (Hot Reload)

**For Backend Development:**

```bash
# Stop containerized API
docker compose stop api

# Run API locally with auto-reload
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**For Frontend Development:**

```bash
# Stop containerized frontend
docker compose stop frontend

# Run frontend locally with Vite dev server
cd frontend
npm install
npm run dev
# Frontend now at http://localhost:5173 with hot reload
```

**For Telemetry Service Development:**

```bash
# Stop containerized telemetry
docker compose stop telemetry

# Run telemetry locally
cd telemetry
pip install -r requirements.txt
python main.py
```

### 8.9 Testing Commands

**Run Unit Tests:**
```bash
docker compose exec api pytest tests/unit/ -v
```

**Run Integration Tests:**
```bash
docker compose exec api pytest tests/integration/ -v
```

**Run E2E Tests:**
```bash
docker compose exec api pytest tests/e2e/ -v
```

**Run All Tests with Coverage:**
```bash
docker compose exec api pytest tests/ -v --cov=app --cov-report=html
# Coverage report at backend/htmlcov/index.html
```

**Run Specific Test File:**
```bash
docker compose exec api pytest tests/unit/test_rule_evaluator.py -v
```

**Run Specific Test Function:**
```bash
docker compose exec api pytest tests/unit/test_rule_evaluator.py::test_evaluate_simple_condition -v
```

### 8.10 Useful Database Queries

**Check Active Devices:**
```sql
SELECT d.id, d.device_key, d.name, d.status,
       (SELECT COUNT(*) FROM device_parameters WHERE device_id = d.id) as param_count
FROM devices d
WHERE d.factory_id = '<your-factory-id>';
```

**View Recent Alerts:**
```sql
SELECT a.id, r.name as rule_name, d.device_key, a.severity, a.message, a.triggered_at
FROM alerts a
JOIN rules r ON a.rule_id = r.id
JOIN devices d ON a.device_id = d.id
WHERE a.factory_id = '<your-factory-id>'
ORDER BY a.triggered_at DESC
LIMIT 20;
```

**Check Analytics Jobs:**
```sql
SELECT id, analysis_type, status, created_at, completed_at,
       TIMESTAMPDIFF(SECOND, created_at, completed_at) as duration_seconds
FROM analytics_jobs
WHERE factory_id = '<your-factory-id>'
ORDER BY created_at DESC
LIMIT 10;
```

**View Device Parameters:**
```sql
SELECT dp.parameter_key, dp.data_type, dp.is_kpi_selected, dp.discovered_at
FROM device_parameters dp
WHERE dp.device_id = <device-id>
ORDER BY dp.parameter_key;
```


## 9. How To Extend

### 9.1 Adding a New API Endpoint

**Scenario:** Add endpoint to get device uptime statistics

**Step 1: Define Response Schema**

Create/update `backend/app/schemas/device.py`:

```python
from pydantic import BaseModel
from datetime import datetime

class DeviceUptimeResponse(BaseModel):
    device_id: int
    device_key: str
    total_uptime_hours: float
    uptime_percentage: float
    last_online: datetime | None
    last_offline: datetime | None
```

**Step 2: Add Repository Function (if needed)**

Update `backend/app/repositories/device_repo.py`:

```python
async def get_uptime_stats(
    db: AsyncSession,
    factory_id: str,
    device_id: int,
    start: datetime,
    end: datetime
) -> dict:
    """Calculate device uptime from status change logs."""
    # Implementation would query device_status_logs table
    # For now, simplified version:
    device = await get_by_id(db, factory_id, device_id)
    if not device:
        return None
    
    # Query InfluxDB for online/offline events
    # ... implementation ...
    
    return {
        "total_uptime_hours": 156.5,
        "uptime_percentage": 98.2,
        "last_online": datetime.utcnow(),
        "last_offline": datetime.utcnow() - timedelta(hours=2)
    }
```

**Step 3: Add API Route**

Update `backend/app/api/v1/devices.py`:

```python
from app.schemas.device import DeviceUptimeResponse

@router.get("/devices/{device_id}/uptime", response_model=DeviceUptimeResponse)
async def get_device_uptime(
    device_id: int,
    start: datetime = Query(..., description="Start time"),
    end: datetime = Query(..., description="End time"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get device uptime statistics for date range."""
    
    # Log request
    logger.info(
        "device.uptime_requested",
        factory_id=current_user.factory_id,
        device_id=device_id,
        user_id=current_user.id,
        start=start.isoformat(),
        end=end.isoformat()
    )
    
    # Fetch device (enforces factory isolation)
    device = await device_repo.get_by_id(db, current_user.factory_id, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Calculate uptime stats
    stats = await device_repo.get_uptime_stats(
        db,
        current_user.factory_id,
        device_id,
        start,
        end
    )
    
    return DeviceUptimeResponse(
        device_id=device.id,
        device_key=device.device_key,
        **stats
    )
```

**Step 4: Test Endpoint**

```bash
# Start services
docker compose up -d

# Login to get token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@vpc.com","password":"Admin@123"}' \
  | jq -r '.access_token')

# Test new endpoint
curl "http://localhost:8000/api/v1/devices/1/uptime?start=2026-02-01T00:00:00Z&end=2026-02-19T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Step 5: Add Frontend Hook (Optional)**

Create `frontend/src/hooks/useDeviceUptime.ts`:

```typescript
import { useState } from 'react';
import api from '../api/client';

interface UptimeStats {
  device_id: number;
  device_key: string;
  total_uptime_hours: number;
  uptime_percentage: number;
  last_online: string;
  last_offline: string;
}

export const useDeviceUptime = (deviceId: number) => {
  const [stats, setStats] = useState<UptimeStats | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchUptime = async (start: Date, end: Date) => {
    setLoading(true);
    try {
      const response = await api.get(`/devices/${deviceId}/uptime`, {
        params: {
          start: start.toISOString(),
          end: end.toISOString()
        }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch uptime:', error);
    } finally {
      setLoading(false);
    }
  };

  return { stats, loading, fetchUptime };
};
```

**Step 6: Use in Frontend Component**

```tsx
// In DeviceDetail.tsx or new component
import { useDeviceUptime } from '../hooks/useDeviceUptime';

function DeviceUptimeCard({ deviceId }: { deviceId: number }) {
  const { stats, loading, fetchUptime } = useDeviceUptime(deviceId);

  useEffect(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30); // Last 30 days
    fetchUptime(start, end);
  }, [deviceId]);

  if (loading) return <div>Loading...</div>;
  if (!stats) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Uptime Statistics</h3>
      <div className="space-y-2">
        <p>Uptime: {stats.uptime_percentage.toFixed(1)}%</p>
        <p>Total Hours: {stats.total_uptime_hours.toFixed(1)}h</p>
        <p>Last Online: {new Date(stats.last_online).toLocaleString()}</p>
      </div>
    </div>
  );
}
```

### 9.2 Adding a New Device Type

**Scenario:** Add support for "Temperature Sensors" in addition to "Machines"

**Step 1: Update Device Model (if type-specific fields needed)**

If all device types share same schema, no change needed. Otherwise, update `backend/app/models/device.py`:

```python
class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    factory_id = Column(String(36), ForeignKey("factories.id"), nullable=False)
    device_key = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False)  # ← Add this if not exists
    # ... rest of fields ...
```

**Step 2: Create Migration**

```bash
docker compose exec api alembic revision --autogenerate -m "add_device_type_field"
docker compose exec api alembic upgrade head
```

**Step 3: Update Device Creation Schema**

Update `backend/app/schemas/device.py`:

```python
from enum import Enum

class DeviceType(str, Enum):
    MACHINE = "machine"
    SENSOR = "sensor"
    GATEWAY = "gateway"

class DeviceCreate(BaseModel):
    device_key: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    device_type: DeviceType = DeviceType.MACHINE  # ← Add this
    location: str | None = None
```

**Step 4: Update Seed Script**

Update `backend/scripts/seed.py`:

```python
# Add temperature sensors
sensor1 = await device_repo.create(
    db,
    factory_id=factory.id,
    device_key="TEMP01",
    name="Temperature Sensor - Zone A",
    device_type="sensor",  # ← New type
    location="Production Floor - Zone A"
)
print(f"✓ Device '{sensor1.name}' created")
```

**Step 5: Update Frontend Type Definitions**

Update `frontend/src/types/index.ts`:

```typescript
export enum DeviceType {
  MACHINE = 'machine',
  SENSOR = 'sensor',
  GATEWAY = 'gateway'
}

export interface Device {
  id: number;
  device_key: string;
  name: string;
  device_type: DeviceType;  // ← Add this
  status: 'online' | 'offline' | 'warning';
  location?: string;
  last_seen?: string;
}
```

**Step 6: Add Type-Specific UI (Optional)**

In `Machines.tsx`, add filtering by type:

```tsx
function Machines() {
  const { devices } = useDevices();
  const [selectedType, setSelectedType] = useState<DeviceType | 'all'>('all');

  const filteredDevices = devices.filter(d =>
    selectedType === 'all' || d.device_type === selectedType
  );

  return (
    <div>
      {/* Filter buttons */}
      <div className="mb-4 space-x-2">
        <button onClick={() => setSelectedType('all')}>All</button>
        <button onClick={() => setSelectedType(DeviceType.MACHINE)}>Machines</button>
        <button onClick={() => setSelectedType(DeviceType.SENSOR)}>Sensors</button>
      </div>

      {/* Device table */}
      <table>
        {/* ... */}
      </table>
    </div>
  );
}
```

**Step 7: Publish Telemetry for New Device Type**

```bash
mosquitto_pub -h localhost -p 1883 \
  -t "factories/vpc/devices/TEMP01/telemetry" \
  -m '{"metrics":{"temperature":23.5,"humidity":45.2}}'
```

Telemetry service auto-discovers parameters (temperature, humidity) regardless of device type.

### 9.3 Adding a New Alert Type

**Scenario:** Add "Predictive Maintenance" alert type that triggers based on ML model output

**Step 1: Define Alert Type**

Update `backend/app/models/alert.py`:

```python
class AlertType(str, enum.Enum):
    THRESHOLD = "threshold"          # Existing: parameter exceeds threshold
    PREDICTIVE = "predictive"        # New: ML predicts failure
    ANOMALY = "anomaly"              # New: Anomaly detected
    MANUAL = "manual"                # New: User-triggered alert
```

**Step 2: Update Alert Model**

```python
class Alert(Base):
    __tablename__ = "alerts"
    
    # ... existing fields ...
    alert_type = Column(Enum(AlertType), nullable=False, default=AlertType.THRESHOLD)
    prediction_data = Column(JSON, nullable=True)  # ML model output
```

**Step 3: Create Migration**

```bash
docker compose exec api alembic revision --autogenerate -m "add_alert_types"
docker compose exec api alembic upgrade head
```

**Step 4: Create Predictive Alert Worker Task**

Create `backend/app/workers/predictive_alerts.py`:

```python
from app.workers.celery_app import celery_app
from app.core.database import get_db_sync
from app.repositories import alert_repo, device_repo
import structlog

logger = structlog.get_logger()

@celery_app.task(name="check_predictive_maintenance", queue="analytics")
def check_predictive_maintenance_task(factory_id: str, device_id: int, prediction: dict):
    """
    Create predictive maintenance alert if failure probability is high.
    
    Args:
        factory_id: Factory UUID
        device_id: Device ID
        prediction: {
            "failure_probability": 0.85,
            "component": "bearing",
            "estimated_days_to_failure": 3
        }
    """
    db = get_db_sync()
    
    try:
        # Threshold: trigger if probability > 70%
        if prediction["failure_probability"] > 0.70:
            alert_id = alert_repo.create_sync(
                db,
                factory_id=factory_id,
                device_id=device_id,
                rule_id=None,  # Not tied to a rule
                alert_type="predictive",
                severity="high",
                message=f"Predictive maintenance required: {prediction['component']} "
                        f"has {prediction['failure_probability']*100:.0f}% failure risk "
                        f"(~{prediction['estimated_days_to_failure']} days)",
                prediction_data=prediction
            )
            
            logger.info(
                "alert.predictive_created",
                factory_id=factory_id,
                device_id=device_id,
                alert_id=alert_id,
                component=prediction["component"],
                probability=prediction["failure_probability"]
            )
            
            # Trigger notification
            from app.workers.notifications import send_notification_task
            send_notification_task.delay(alert_id)
    
    except Exception as e:
        logger.error(
            "predictive_alert.failed",
            factory_id=factory_id,
            device_id=device_id,
            error=str(e)
        )
        raise
```

**Step 5: Trigger Predictive Alert**

From analytics job completion:

```python
# In backend/app/workers/analytics.py

# After ML model runs:
if analysis_type == "predictive_maintenance":
    for device_id, prediction in results.items():
        from app.workers.predictive_alerts import check_predictive_maintenance_task
        check_predictive_maintenance_task.delay(
            factory_id=factory_id,
            device_id=device_id,
            prediction=prediction
        )
```

**Step 6: Display in Frontend**

Update `frontend/src/pages/Dashboard.tsx` to show predictive alerts differently:

```tsx
function AlertRow({ alert }: { alert: Alert }) {
  const isPredictive = alert.alert_type === 'predictive';

  return (
    <tr>
      <td>
        {isPredictive && (
          <span className="inline-flex items-center text-purple-600">
            🔮 Predictive
          </span>
        )}
        {alert.message}
      </td>
      {isPredictive && alert.prediction_data && (
        <td>
          <div className="text-sm text-gray-600">
            Probability: {(alert.prediction_data.failure_probability * 100).toFixed(0)}%
          </div>
        </td>
      )}
    </tr>
  );
}
```

### 9.4 Adding a New Frontend Page

**Scenario:** Add "Energy Dashboard" page showing power consumption trends

**Step 1: Create Page Component**

Create `frontend/src/pages/EnergyDashboard.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useDevices } from '../hooks/useDevices';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../api/client';

interface EnergyData {
  timestamp: string;
  total_power: number;
  device_breakdown: Record<string, number>;
}

export default function EnergyDashboard() {
  const { devices } = useDevices();
  const [energyData, setEnergyData] = useState<EnergyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('24h');

  useEffect(() => {
    fetchEnergyData();
    const interval = setInterval(fetchEnergyData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [timeRange]);

  const fetchEnergyData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/energy/consumption', {
        params: { range: timeRange }
      });
      setEnergyData(response.data.data);
    } catch (error) {
      console.error('Failed to fetch energy data:', error);
    } finally {
      setLoading(false);
    }
  };

  const totalEnergy = energyData.reduce((sum, d) => sum + d.total_power, 0);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Energy Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Energy (kWh)</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">
            {(totalEnergy / 1000).toFixed(2)}
          </p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Active Devices</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">
            {devices.filter(d => d.status === 'online').length}
          </p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Avg Power (W)</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">
            {energyData.length > 0 ? (totalEnergy / energyData.length).toFixed(0) : '—'}
          </p>
        </div>
      </div>

      {/* Time Range Selector */}
      <div className="mb-4">
        <button
          onClick={() => setTimeRange('1h')}
          className={`px-4 py-2 rounded ${timeRange === '1h' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          1 Hour
        </button>
        <button
          onClick={() => setTimeRange('24h')}
          className={`px-4 py-2 rounded ml-2 ${timeRange === '24h' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          24 Hours
        </button>
        <button
          onClick={() => setTimeRange('7d')}
          className={`px-4 py-2 rounded ml-2 ${timeRange === '7d' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          7 Days
        </button>
      </div>

      {/* Energy Consumption Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Power Consumption Over Time</h2>
        {loading ? (
          <div className="h-96 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={energyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis label={{ value: 'Power (W)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="total_power" stroke="#2563eb" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Add Route**

Update `frontend/src/App.tsx`:

```tsx
import EnergyDashboard from './pages/EnergyDashboard';

function App() {
  return (
    <Routes>
      {/* ... existing routes ... */}
      <Route path="/energy" element={<EnergyDashboard />} />
    </Routes>
  );
}
```

**Step 3: Add Navigation Link**

Update `frontend/src/components/ui/Sidebar.tsx`:

```tsx
<nav>
  {/* ... existing links ... */}
  <a href="/energy" className="flex items-center px-4 py-2 text-gray-700 hover:bg-gray-100">
    ⚡ Energy
  </a>
</nav>
```

**Step 4: Create Backend Endpoint**

Create `backend/app/api/v1/energy.py`:

```python
from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.kpi_service import query_influxdb
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/energy/consumption")
async def get_energy_consumption(
    range: str = Query("24h", regex="^(1h|24h|7d)$"),
    current_user: User = Depends(get_current_user)
):
    """Get total power consumption for all devices."""
    
    # Parse time range
    range_map = {"1h": 1, "24h": 24, "7d": 168}
    hours = range_map[range]
    
    start = datetime.utcnow() - timedelta(hours=hours)
    end = datetime.utcnow()
    
    # Query InfluxDB for all devices' power consumption
    query = f'''
    from(bucket: "factoryops")
      |> range(start: {start.isoformat()}Z, stop: {end.isoformat()}Z)
      |> filter(fn: (r) => r["factory_id"] == "{current_user.factory_id}")
      |> filter(fn: (r) => r["_field"] == "power")
      |> aggregateWindow(every: {60 if hours <= 24 else 3600}s, fn: mean)
    '''
    
    result = await query_influxdb(query)
    
    # Process results
    data = []
    for record in result:
        data.append({
            "timestamp": record["_time"],
            "total_power": record["_value"],
            "device_key": record.get("device_key")
        })
    
    return {"data": data, "range": range}
```

**Step 5: Register Router**

Update `backend/app/main.py`:

```python
from app.api.v1 import energy

app.include_router(energy.router, prefix="/api/v1", tags=["energy"])
```

### 9.5 Adding a New Celery Task

**Scenario:** Add daily summary email task

**Step 1: Create Task**

Create `backend/app/workers/daily_summary.py`:

```python
from app.workers.celery_app import celery_app
from app.core.database import get_db_sync
from app.repositories import factory_repo, device_repo, alert_repo
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

@celery_app.task(name="send_daily_summary", queue="reporting")
def send_daily_summary_task(factory_id: str):
    """Send daily summary email to factory admins."""
    
    db = get_db_sync()
    
    try:
        # Gather stats
        factory = factory_repo.get_by_id_sync(db, factory_id)
        devices = device_repo.get_all_sync(db, factory_id)
        
        yesterday = datetime.utcnow() - timedelta(days=1)
        alerts_24h = alert_repo.get_by_time_range_sync(
            db, factory_id, yesterday, datetime.utcnow()
        )
        
        # Build email
        email_body = f"""
        Daily Summary for {factory.name}
        Date: {datetime.utcnow().strftime('%Y-%m-%d')}
        
        📊 Statistics:
        - Total Devices: {len(devices)}
        - Online: {sum(1 for d in devices if d.status == 'online')}
        - Alerts (24h): {len(alerts_24h)}
        
        🚨 Critical Alerts:
        {chr(10).join(f"- {a.message}" for a in alerts_24h if a.severity == 'critical')}
        """
        
        # Send email to all admins
        admins = factory_repo.get_admins_sync(db, factory_id)
        for admin in admins:
            # Use existing notification service
            from app.workers.notifications import _send_email
            _send_email(admin.email, "Daily Factory Summary", email_body)
        
        logger.info(
            "daily_summary.sent",
            factory_id=factory_id,
            recipient_count=len(admins)
        )
    
    except Exception as e:
        logger.error("daily_summary.failed", factory_id=factory_id, error=str(e))
        raise
```

**Step 2: Schedule Task with Celery Beat**

Update `backend/app/workers/celery_app.py`:

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'daily-summary-all-factories': {
        'task': 'send_daily_summary',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
        'args': ()  # Need to iterate factories
    },
}
```

**Better approach - iterate all factories:**

```python
@celery_app.task(name="trigger_all_daily_summaries")
def trigger_all_daily_summaries_task():
    """Trigger daily summary for all factories."""
    db = get_db_sync()
    factories = factory_repo.get_all_sync(db)
    
    for factory in factories:
        send_daily_summary_task.delay(factory.id)

# Schedule this task instead:
celery_app.conf.beat_schedule = {
    'daily-summary-all-factories': {
        'task': 'trigger_all_daily_summaries',
        'schedule': crontab(hour=8, minute=0),
    },
}
```

**Step 3: Test Task Manually**

```bash
# Execute task immediately
docker compose exec worker python -c "
from app.workers.daily_summary import send_daily_summary_task
send_daily_summary_task.delay('f7c8d9e0-1234-5678-90ab-cdef12345678')
"

# Check logs
docker compose logs -f worker | grep "daily_summary"
```


## 10. Deployment

### 10.1 Local Development Setup

**Prerequisites:**
```bash
# Required software
- Docker Desktop 24.x+
- Docker Compose 2.x+
- Git
- Python 3.11+ (for local backend development)
- Node.js 18+ (for local frontend development)
```

**Step-by-Step Setup:**

```bash
# 1. Clone repository
git clone <repo-url>
cd factoryops

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
cd docker
docker compose up -d

# 4. Wait for services to be healthy (30-60 seconds)
docker compose ps

# 5. Run database migrations
docker compose exec api alembic upgrade head

# 6. Seed initial data
docker compose exec api python scripts/seed.py

# 7. Verify setup
curl http://localhost:8000/health
# Should return: {"status": "ok", ...}

# 8. Access application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

**Default Login Credentials:**
- Email: `admin@vpc.com`
- Password: `Admin@123`
- Factory: VPC Manufacturing

---

### 10.2 Environment Variables Explained

Every environment variable in `.env.example`:

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| **Backend API** |
| `DATABASE_URL` | ✅ | - | MySQL connection string | `mysql+aiomysql://root:password@mysql:3306/factoryops` |
| `SECRET_KEY` | ✅ | - | JWT signing key (generate with `openssl rand -hex 32`) | `abc123...` |
| `REDIS_URL` | ✅ | - | Redis connection for caching | `redis://redis:6379/0` |
| `INFLUXDB_URL` | ✅ | - | InfluxDB API endpoint | `http://influxdb:8086` |
| `INFLUXDB_TOKEN` | ✅ | - | InfluxDB auth token | `your-token` |
| `INFLUXDB_ORG` | ✅ | `factoryops` | InfluxDB organization | `factoryops` |
| `INFLUXDB_BUCKET` | ✅ | `telemetry` | InfluxDB bucket name | `telemetry` |
| `MINIO_ENDPOINT` | ✅ | - | MinIO S3-compatible storage | `minio:9000` |
| `MINIO_ACCESS_KEY` | ✅ | - | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | ✅ | - | MinIO secret key | `minioadmin` |
| `MINIO_BUCKET` | ✅ | `factoryops` | MinIO bucket name | `factoryops` |
| `CELERY_BROKER_URL` | ✅ | - | Celery broker (Redis) | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | ✅ | - | Celery results storage | `redis://redis:6379/2` |
| **Telemetry Service** |
| `MQTT_BROKER` | ✅ | `mosquitto` | MQTT broker hostname | `mosquitto` |
| `MQTT_PORT` | ✅ | `1883` | MQTT broker port | `1883` |
| `MQTT_USERNAME` | ❌ | - | MQTT auth username (optional) | - |
| `MQTT_PASSWORD` | ❌ | - | MQTT auth password (optional) | - |
| **Notifications** |
| `SMTP_HOST` | ❌ | - | Email SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | ❌ | `587` | SMTP port | `587` |
| `SMTP_USERNAME` | ❌ | - | SMTP auth username | `your-email@gmail.com` |
| `SMTP_PASSWORD` | ❌ | - | SMTP auth password | `app-password` |
| `SMTP_FROM_EMAIL` | ❌ | - | From address for emails | `alerts@factoryops.com` |
| `TWILIO_ACCOUNT_SID` | ❌ | - | Twilio account ID (for WhatsApp) | `ACxxx...` |
| `TWILIO_AUTH_TOKEN` | ❌ | - | Twilio auth token | `xxx...` |
| `TWILIO_WHATSAPP_FROM` | ❌ | - | Twilio WhatsApp sender number | `whatsapp:+14155238886` |
| **Analytics** |
| `OPENAI_API_KEY` | ❌ | - | OpenAI API key (for AI co-pilot analytics) | `sk-...` |
| **Frontend** |
| `VITE_API_BASE_URL` | ✅ | `http://localhost:8000` | Backend API base URL | `http://localhost:8000` |

**Security Notes:**
- ⚠️ **NEVER** commit `.env` to version control
- ⚠️ Generate strong `SECRET_KEY` in production: `openssl rand -hex 32`
- ⚠️ Change all default passwords (`MYSQL_ROOT_PASSWORD`, `MINIO_ACCESS_KEY`, etc.)
- ⚠️ Use secrets management in production (Docker secrets, AWS Secrets Manager, etc.)

---

### 10.3 Production Deployment

**Prerequisites:**
- Ubuntu 22.04 LTS server (8+ cores, 16GB+ RAM, 100GB+ SSD)
- Domain name with DNS configured
- SSL/TLS certificate (Let's Encrypt recommended)
- Docker & Docker Compose installed

**Production Checklist:**

```bash
# 1. Create Docker secrets (DO NOT use .env in production)
echo "strong-secret-key" | docker secret create factoryops_secret_key -
echo "mysql-root-password" | docker secret create mysql_root_password -
echo "influxdb-admin-token" | docker secret create influxdb_token -
# ... create all secrets

# 2. Update nginx/nginx.prod.conf with your domain
# Replace factoryops.example.com with your domain

# 3. Place SSL certificates
mkdir -p /etc/nginx/ssl
cp your-cert.crt /etc/nginx/ssl/factoryops.crt
cp your-cert.key /etc/nginx/ssl/factoryops.key

# 4. Deploy with production compose file
docker compose -f docker/docker-compose.prod.yml up -d

# 5. Run migrations
docker compose -f docker/docker-compose.prod.yml exec api alembic upgrade head

# 6. Create first super admin
docker compose -f docker/docker-compose.prod.yml exec api python scripts/seed.py

# 7. Verify deployment
curl https://your-domain.com/health

# 8. Setup automated backups (cron job)
sudo crontab -e
# Add line:
# 0 2 * * * /path/to/factoryops/scripts/backup.sh
```

**Production Environment Variables:**

Must override in production:
```bash
DATABASE_URL=mysql+aiomysql://factoryops:STRONG_PASSWORD@mysql:3306/factoryops
SECRET_KEY=<64-char-hex-string>
REDIS_URL=redis://:REDIS_PASSWORD@redis:6379/0
INFLUXDB_TOKEN=<strong-token>
MINIO_ACCESS_KEY=<strong-key>
MINIO_SECRET_KEY=<strong-secret>
SMTP_HOST=smtp.yourdomain.com
SMTP_USERNAME=alerts@yourdomain.com
SMTP_PASSWORD=<app-password>
TWILIO_ACCOUNT_SID=<your-sid>
TWILIO_AUTH_TOKEN=<your-token>
```

---

### 10.4 CI/CD Pipeline

**GitHub Actions Workflow** (`.github/workflows/ci.yml`):

**Triggered on:**
- Push to `main` branch
- Pull request to `main`

**Pipeline Stages:**

1. **Lint** (3-5 minutes)
   - Python: Ruff linting (`ruff check`)
   - Python: Format check (`ruff format --check`)
   - TypeScript: ESLint (`npm run lint`)

2. **Test** (5-10 minutes)
   - Spin up MySQL, Redis, InfluxDB in Docker
   - Run Alembic migrations
   - Run pytest (unit + integration + E2E)
   - Generate coverage report
   - Upload to Codecov (if configured)

3. **Build** (5-10 minutes)
   - Build Docker images (api, telemetry, frontend)
   - Tag with git SHA
   - Push to GitHub Container Registry (GHCR)

4. **Security Scan** (2-5 minutes)
   - Trivy vulnerability scan on Docker images
   - Fail on CRITICAL vulnerabilities
   - Report on HIGH vulnerabilities

**Required GitHub Secrets:**
- `GHCR_TOKEN`: GitHub token for container registry push
- `CODECOV_TOKEN`: (Optional) For coverage reporting

**Deployment:**
```bash
# Manual deployment from CI artifacts
docker pull ghcr.io/your-org/factoryops-api:latest
docker pull ghcr.io/your-org/factoryops-telemetry:latest
docker pull ghcr.io/your-org/factoryops-frontend:latest

# Update and restart services
docker compose -f docker/docker-compose.prod.yml pull
docker compose -f docker/docker-compose.prod.yml up -d
```

---

### 10.5 Monitoring & Observability

**Prometheus Metrics:**
```bash
# Available at: http://localhost:8000/api/v1/metrics

# Key metrics exposed:
factoryops_telemetry_messages_total{factory_id}
factoryops_alerts_triggered_total{factory_id, severity}
factoryops_notifications_sent_total{channel, status}
factoryops_celery_tasks_total{queue, status}
factoryops_api_request_duration_seconds{method, endpoint, status_code}
factoryops_telemetry_write_latency_seconds
factoryops_kpi_query_latency_seconds
factoryops_active_rules_total{factory_id}
factoryops_active_devices_total{factory_id}
```

**Recommended Grafana Dashboards:**
1. **Telemetry Overview**: Message throughput, write latency, error rates
2. **API Performance**: Request duration, status codes, endpoint breakdown
3. **Alerts & Notifications**: Alert triggers by severity, notification success rate
4. **System Health**: Database connections, Redis hits/misses, InfluxDB cardinality

**Health Check Endpoint:**
```bash
curl http://localhost:8000/health

# Response:
{
  "status": "ok",
  "timestamp": "2026-02-19T00:00:00Z",
  "version": "1.0.0",
  "dependencies": {
    "database": "ok",
    "redis": "ok",
    "influxdb": "ok",
    "minio": "ok"
  }
}
```

**Structured Logging:**

All services use `structlog` for JSON logging. Every log entry includes:
- `timestamp`: ISO 8601 timestamp
- `level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `event`: Event name (e.g., "telemetry.processed", "alert.triggered")
- `factory_id`: Factory ID (where applicable)
- `request_id`: Unique request ID for tracing

Example log entry:
```json
{
  "timestamp": "2026-02-19T00:00:00.123Z",
  "level": "info",
  "event": "telemetry.processed",
  "factory_id": 1,
  "device_id": 5,
  "metric_count": 4,
  "write_latency_ms": 12.5
}
```

**Viewing Logs:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f telemetry
docker compose logs -f celery-worker

# Tail last 100 lines
docker compose logs --tail=100 api

# Filter by level (using jq)
docker compose logs api | jq 'select(.level == "error")'

# Follow alerts in real-time
docker compose logs -f celery-worker | grep "alert.triggered"
```

---

### 10.6 Backup & Restore

**Automated Backup Script:** `scripts/backup.sh`

```bash
# Schedule with cron (daily at 2 AM)
0 2 * * * /path/to/factoryops/scripts/backup.sh

# Manual backup
./scripts/backup.sh

# Backup creates:
# 1. MySQL dump: /backups/mysql_YYYYMMDD_HHMMSS.sql.gz
# 2. Uploads to MinIO: backups/ bucket
# 3. Keeps last 30 days, deletes older
```

**Manual Backup:**
```bash
# MySQL
docker compose exec mysql mysqldump -u root -p factoryops | gzip > backup_$(date +%Y%m%d).sql.gz

# InfluxDB
docker compose exec influxdb influx backup /tmp/influx-backup
docker cp influxdb:/tmp/influx-backup ./influx-backup-$(date +%Y%m%d)

# MinIO (application files)
# Use MinIO client (mc) or AWS CLI
```

**Restore from Backup:**
```bash
# MySQL
gunzip < backup_20260219.sql.gz | docker compose exec -T mysql mysql -u root -p factoryops

# InfluxDB
docker cp influx-backup-20260219 influxdb:/tmp/influx-restore
docker compose exec influxdb influx restore /tmp/influx-restore
```

---

### 10.7 Scaling Guide

**Horizontal Scaling:**

1. **API Service** (stateless, easily scalable):
```yaml
# docker-compose.prod.yml
api:
  deploy:
    replicas: 3  # Increase replicas
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

2. **Celery Workers** (scale per queue):
```bash
# Add more workers for specific queues
docker compose -f docker-compose.prod.yml up -d --scale celery-worker=5
docker compose -f docker-compose.prod.yml up -d --scale celery-beat=1

# Or separate workers per queue:
# - celery-worker-rules (queue: rules)
# - celery-worker-analytics (queue: analytics)
# - celery-worker-reporting (queue: reporting)
# - celery-worker-notifications (queue: notifications)
```

3. **Telemetry Service** (single instance, scale vertically):
```yaml
# Increase resources
telemetry:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 4G
```

**Vertical Scaling (Resource Limits):**

Current production limits (`docker-compose.prod.yml`):
- **MySQL**: 2 CPUs, 4GB RAM
- **InfluxDB**: 4 CPUs, 8GB RAM (time-series heavy)
- **Redis**: 1 CPU, 2GB RAM
- **API**: 2 CPUs, 2GB RAM
- **Celery Worker**: 2 CPUs, 2GB RAM
- **Telemetry**: 2 CPUs, 1GB RAM

**Database Scaling:**

- **MySQL**: Use read replicas for reporting queries
- **InfluxDB**: Increase retention policy, use downsampling for old data
- **Redis**: Enable Redis Cluster for > 10GB datasets

**When to Scale:**

Monitor these metrics:
- API response time > 500ms (scale API replicas)
- Celery queue length > 100 (scale workers)
- Memory usage > 80% (increase limits)
- CPU usage > 70% sustained (increase limits or replicas)
- InfluxDB write latency > 100ms (scale InfluxDB vertically)

---

### 10.8 Troubleshooting Production Issues

**Issue: API returns 500 errors**

```bash
# Check API logs
docker compose logs --tail=100 api | grep "error"

# Check database connectivity
docker compose exec api python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"

# Check all dependencies
curl http://localhost:8000/health
```

**Issue: Telemetry not processing**

```bash
# Check MQTT broker
docker compose logs mosquitto | tail -50

# Check telemetry service
docker compose logs telemetry | grep "error"

# Verify MQTT subscription
docker compose exec mosquitto mosquitto_sub -t "factories/#" -v

# Publish test message
docker compose exec mosquitto mosquitto_pub \
  -t "factories/vpc/devices/M01/telemetry" \
  -m '{"metrics":{"test":123}}'
```

**Issue: Rules not triggering**

```bash
# Check Celery worker
docker compose logs celery-worker | grep "rule_engine"

# Check Redis connection
docker compose exec redis redis-cli ping

# Manually trigger rule evaluation
docker compose exec api python -c "
from app.workers.celery_app import celery_app
from app.workers.rule_engine import evaluate_rules_task
result = evaluate_rules_task.delay(factory_id=1, device_id=1, metrics={'voltage': 250})
print(f'Task ID: {result.id}')
"
```

**Issue: High memory usage**

```bash
# Check container stats
docker stats --no-stream

# Find memory-heavy processes
docker compose exec api top

# Check InfluxDB cardinality (can cause memory issues)
docker compose exec influxdb influx query \
  'SELECT COUNT(*) FROM "telemetry" GROUP BY "device_id"'
```

**Issue: Slow dashboard loading**

```bash
# Check API response times
docker compose logs nginx | grep "request_time"

# Check InfluxDB query performance
docker compose logs influxdb | grep "query"

# Enable query logging
# backend/app/core/influx.py - set debug=True

# Check Redis cache hit rate
docker compose exec redis redis-cli INFO stats | grep keyspace
```

---

## Appendix A: Complete Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** |
| Framework | React | 18.3.x | UI framework |
| Language | TypeScript | 5.x | Type-safe JavaScript |
| Build Tool | Vite | 5.x | Fast build tool |
| Styling | Tailwind CSS | 3.x | Utility-first CSS |
| Charts | Recharts | 2.x | Data visualization |
| State | Zustand | 4.x | Lightweight state management |
| HTTP Client | Axios | 1.x | API requests |
| **Backend API** |
| Framework | FastAPI | 0.110.x | Modern Python web framework |
| Language | Python | 3.11 | Programming language |
| ASGI Server | Uvicorn | 0.29.x | ASGI server |
| ORM | SQLAlchemy | 2.0.x | Async ORM |
| Migrations | Alembic | 1.13.x | Database migrations |
| Validation | Pydantic | 2.x | Data validation |
| Auth | python-jose | 3.3.x | JWT handling |
| Password | passlib | 1.7.x | Password hashing (bcrypt) |
| **Telemetry Service** |
| Protocol | MQTT | 3.1.1/5.0 | IoT messaging |
| Client | paho-mqtt | 2.1.x | MQTT client library |
| Framework | FastAPI | 0.110.x | HTTP endpoints |
| **Background Workers** |
| Task Queue | Celery | 5.3.x | Distributed task queue |
| Broker | Redis | 7.x | Message broker |
| **Databases** |
| Metadata DB | MySQL | 8.0 | Relational database |
| Time-Series DB | InfluxDB | 2.7 | Time-series database |
| Cache | Redis | 7.0 | In-memory cache |
| Object Storage | MinIO | Latest | S3-compatible storage |
| MQTT Broker | Mosquitto | 2.0 | MQTT broker |
| **Infrastructure** |
| Container | Docker | 24.x | Containerization |
| Orchestration | Docker Compose | 2.x | Multi-container apps |
| Reverse Proxy | NGINX | 1.25 | Load balancer & TLS |
| **Observability** |
| Metrics | Prometheus | - | Metrics collection |
| Logging | structlog | 24.x | Structured logging |
| Monitoring | Grafana | - | Visualization (recommended) |
| **CI/CD** |
| Pipeline | GitHub Actions | - | CI/CD automation |
| Linting | Ruff | 0.3.x | Python linting |
| Testing | pytest | 8.x | Testing framework |
| Security Scan | Trivy | Latest | Container vulnerability scan |
| **Development** |
| Editor | VS Code | - | Recommended IDE |
| Python Env | venv/poetry | - | Virtual environment |
| Node Package | npm | 10.x | Node package manager |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Factory** | A manufacturing facility. Each factory is isolated from others (multi-tenant). |
| **Device** | An IoT sensor/machine that sends telemetry (e.g., CNC machine, motor, sensor). |
| **Telemetry** | Real-time data from devices (voltage, temperature, pressure, etc.). |
| **Parameter** | A specific metric key (e.g., "voltage", "current", "temperature"). |
| **KPI** | Key Performance Indicator - a parameter selected for dashboard display. |
| **Rule** | A conditional expression that triggers alerts (e.g., "voltage > 250"). |
| **Alert** | A triggered notification when a rule condition is met. |
| **Cooldown** | Minimum time between alert triggers to prevent spam. |
| **Analytics Job** | A background task for anomaly detection or forecasting. |
| **Report** | A generated PDF/Excel/JSON document with factory metrics. |
| **MQTT Topic** | Message routing path: `factories/{factory_key}/devices/{device_key}/telemetry` |
| **JWT** | JSON Web Token - used for stateless authentication. |
| **Factory Isolation** | Strict data separation between factories (security requirement). |
| **Celery Task** | Background job (rule evaluation, analytics, notifications, reporting). |
| **InfluxDB Bucket** | Storage location for time-series data. |
| **MinIO Bucket** | Storage location for generated files (reports, analytics results). |

---

## Appendix C: Quick Reference Commands

```bash
# Start all services
docker compose -f docker/docker-compose.yml up -d

# Stop all services
docker compose -f docker/docker-compose.yml down

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f api

# Run migrations
docker compose exec api alembic upgrade head

# Create migration
docker compose exec api alembic revision --autogenerate -m "description"

# Seed database
docker compose exec api python scripts/seed.py

# Run tests
docker compose exec api pytest tests/ -v

# Access MySQL
docker compose exec mysql mysql -u root -p factoryops

# Access Redis CLI
docker compose exec redis redis-cli

# Access InfluxDB CLI
docker compose exec influxdb influx

# Publish test telemetry
docker compose exec mosquitto mosquitto_pub \
  -t "factories/vpc/devices/M01/telemetry" \
  -m '{"metrics":{"voltage":231,"current":3.2}}'

# Subscribe to all MQTT messages
docker compose exec mosquitto mosquitto_sub -t "factories/#" -v

# Restart specific service
docker compose restart api

# Scale Celery workers
docker compose up -d --scale celery-worker=3

# View resource usage
docker stats

# Backup database
./scripts/backup.sh

# Run linting
ruff check backend/ telemetry/

# Format code
ruff format backend/ telemetry/

# Build Docker images
docker compose build

# View API documentation
open http://localhost:8000/api/docs
```

---

## Appendix D: Support & Resources

**Documentation:**
- High-Level Design: `docs/hld_enhanced.md`
- Low-Level Design: `docs/lld_enhanced.md`
- API Specification: `docs/api-spec.md`
- Deployment Guide: `docs/deployment.md`
- Production Readiness: `PRODUCTION_READINESS_REPORT.md`

**Testing:**
- Unit Tests: `backend/tests/unit/`
- Integration Tests: `backend/tests/integration/`
- E2E Tests: `backend/tests/e2e/`
- Test Results: 42/42 passing (100%)

**CI/CD:**
- Pipeline: `.github/workflows/ci.yml`
- Production Compose: `docker/docker-compose.prod.yml`
- NGINX Config: `nginx/nginx.prod.conf`

**Scripts:**
- Database Seed: `backend/scripts/seed.py`
- Backup: `scripts/backup.sh`

---

## Final Notes

This document is **comprehensive** but not exhaustive. For specific implementation details:

1. **Read the code**: All code is well-documented with docstrings
2. **Check the tests**: Tests demonstrate expected behavior
3. **Review the docs**: Technical design docs provide architectural reasoning
4. **Run locally**: Hands-on experience is invaluable

**Remember:** This is a production-ready system. Treat it with care:
- Always test in staging before production
- Never commit secrets to version control
- Always run tests before deploying
- Monitor metrics and logs after deployment
- Keep dependencies updated (security patches)

**Welcome to FactoryOps!** 🏭🤖

---

*Document generated: February 2026*  
*Version: 1.0.0*  
*Last updated by: Rovo Dev*

