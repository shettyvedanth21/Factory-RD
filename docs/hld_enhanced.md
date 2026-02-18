# High-Level Design (HLD)
## FactoryOps AI Engineering — Industrial Energy Intelligence Platform
### Version 2.0 — Production-Grade Specification

---

## 1. System Overview

FactoryOps AI Engineering is a **multi-tenant industrial energy intelligence platform** designed to monitor, analyze, and optimize energy consumption across factories. The system ingests real-time telemetry from industrial devices via MQTT, stores it in a time-series database, evaluates rule-based alerts, and powers AI-driven analytics and structured reporting — all under strict factory-level isolation.

### Key Characteristics

- **Multi-tenant factory isolation** — every request is scoped to a factory; cross-factory access is architecturally impossible
- **Schema-free telemetry ingestion** — parameters discovered dynamically from firmware; no backend changes required
- **Async-first architecture** — telemetry pipeline is never blocked by rule evaluation, analytics, or reporting
- **Self-hosted infrastructure** — no mandatory SaaS dependencies; deployable on-prem or cloud
- **Production-grade observability** — structured logging, metrics, and alerting built in from day one

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                       │
│   Dashboard │ Machines │ Rules │ Analytics │ Reports │ Users  │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTPS / REST + WebSocket
┌────────────────────────▼─────────────────────────────────────┐
│                  NGINX Reverse Proxy (TLS)                    │
└────┬──────────────────────────────────────────┬──────────────┘
     │                                           │
┌────▼─────────┐                    ┌────────────▼─────────────┐
│  API Service │                    │   Telemetry Ingestion     │
│  (FastAPI)   │                    │   Service (Python)        │
│  Port 8000   │                    │   MQTT Subscriber         │
└────┬─────────┘                    └────────────┬─────────────┘
     │                                           │
     │  MySQL (metadata)              InfluxDB (telemetry)
     │  Redis (cache/broker)          Redis (task broker)
     │                                           │
┌────▼──────────────────────────────────────────▼─────────────┐
│                     Celery Workers                            │
│   Rule Engine │ Analytics Worker │ Reporting Worker          │
│   Alert/Notification Service                                  │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│  EMQX MQTT Broker (Port 1883)    │
│  TLS Port: 8883                  │
└──────────────────────────────────┘
     │
     ▼
  Industrial Devices / Factory Floor
```

### Core Services

| Service | Technology | Responsibility |
|---|---|---|
| API Service | FastAPI (Python) | REST API, Auth, Business Logic |
| Telemetry Ingestion | Python (asyncio + aiomqtt) | MQTT subscribe, parse, store |
| Rule Engine | Celery Worker | Evaluate rules against telemetry |
| Analytics Worker | Celery + scikit-learn/Prophet | Run ML jobs |
| Reporting Worker | Celery + ReportLab/openpyxl | Generate PDF/Excel |
| Alert/Notification | Celery + SMTP + Twilio | Send alerts |
| Frontend | React 18 + Vite | SPA Dashboard |

### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Metadata DB | MySQL 8.0 | Users, devices, rules, alerts |
| Time-Series DB | InfluxDB 2.x | All telemetry data |
| Task Broker | Redis 7 | Celery task queue |
| Object Storage | MinIO | Analytics datasets, reports |
| MQTT Broker | EMQX 5.x | Device message broker |
| Reverse Proxy | NGINX | TLS termination, routing |

---

## 3. Core Design Principles

### 3.1 Factory Isolation (Non-Negotiable)

Every layer enforces factory isolation:

1. **MQTT**: Topic namespace `factories/{factory_id}/...` — wildcard subscriber extracts factory from topic
2. **JWT**: Token contains `factory_id` claim; every API handler validates it
3. **Database**: Every MySQL table has `factory_id` column; every query filters by it
4. **InfluxDB**: `factory_id` is a required tag on every measurement
5. **MinIO**: Objects stored under `{factory_id}/` prefix
6. **Celery**: Tasks carry factory context; workers validate before processing

No service method should operate without a `factory_id`. Any function that queries data without factory scope is a bug.

---

### 3.2 Async-First Architecture

The telemetry pipeline is the critical path. Nothing may block it:

- MQTT message received → written to InfluxDB → Celery task dispatched (non-blocking)
- Rule evaluation, analytics, reporting are all background Celery tasks
- API endpoints for analytics/reporting return job IDs; clients poll for results
- Database writes to MySQL (parameter discovery) are async-compatible

**Forbidden in the telemetry path:**
- Synchronous HTTP calls
- Heavy computation
- Blocking file I/O

---

### 3.3 Dynamic Parameter Discovery

When firmware publishes telemetry:
1. Parse all metric keys from payload
2. Check `device_parameters` table for existing entries
3. Auto-insert new parameters with `is_kpi_selected = TRUE`
4. Proceed with InfluxDB write

This enables zero-touch onboarding. New firmware adding a new metric key requires no backend changes.

---

### 3.4 Self-Hosted Stack

All infrastructure runs in Docker containers. Zero external SaaS dependencies for core functionality. Optional integrations (Twilio for WhatsApp, SMTP for email) use environment-variable configuration and can be swapped without code changes.

---

## 4. Technology Stack

### Frontend

| Layer | Technology |
|---|---|
| Framework | React 18 + Vite 5 |
| Styling | Tailwind CSS 3 |
| State Management | Zustand |
| Server State | React Query (TanStack Query v5) |
| Charts | Recharts |
| HTTP Client | Axios |
| Routing | React Router v6 |

### Backend

| Layer | Technology |
|---|---|
| Web Framework | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.0 (async) |
| Auth | python-jose (JWT) + passlib (bcrypt) |
| Validation | Pydantic v2 |
| MQTT Client | aiomqtt (async) |
| Task Queue | Celery 5 + Redis |
| ML | pandas, scikit-learn, Prophet |
| PDF | ReportLab |
| Excel | openpyxl |

### Data Layer

| Layer | Technology |
|---|---|
| Metadata | MySQL 8.0 |
| Telemetry | InfluxDB 2.x |
| Cache/Broker | Redis 7 |
| Object Storage | MinIO (S3-compatible) |
| MQTT | EMQX 5.x |

---

## 5. Security Architecture

### 5.1 Authentication Flow

```
Client → POST /auth/login (factory_id + email + password)
       ← JWT {factory_id, user_id, role, exp}

Client → GET /api/... (Authorization: Bearer <token>)
       → Middleware validates JWT + extracts factory context
       → All downstream calls use factory_id from token
```

### 5.2 JWT Structure

```json
{
  "sub": "user_id",
  "factory_id": "vpc",
  "factory_slug": "vpc",
  "role": "super_admin",
  "exp": 1234567890
}
```

### 5.3 RBAC Permissions

| Action | Super Admin | Admin |
|---|---|---|
| View dashboard | ✓ | ✓ |
| View machines/telemetry | ✓ | ✓ |
| Create/edit rules | ✓ | Configurable |
| Run analytics | ✓ | Configurable |
| Generate reports | ✓ | Configurable |
| Manage users | ✓ | ✗ |
| Invite admins | ✓ | ✗ |

### 5.4 Device Security

- Devices authenticate via API key embedded in MQTT `username`
- EMQX ACL rules enforce topic-level authorization
- Devices may only publish to their own factory/device topic
- TLS required in production (port 8883)

### 5.5 Secrets Management

- All secrets via environment variables (`.env` files in dev)
- Production: use Docker secrets or Kubernetes secrets
- No hardcoded credentials anywhere in codebase
- Secret rotation supported without service restart

---

## 6. Data Flow

### 6.1 Telemetry Ingestion Flow

```
Device → MQTT Publish → EMQX Broker
→ Telemetry Service (wildcard subscriber)
  → Validate payload
  → Extract factory_id + device_id from topic
  → Discover new parameters (MySQL upsert)
  → Write to InfluxDB (batch)
  → Dispatch RuleEngine.evaluate.delay(factory_id, device_id, metrics)
```

### 6.2 API Request Flow

```
Client → NGINX → FastAPI
  → JWT Middleware (validate + extract factory_id)
  → Route Handler
  → Service Layer (business logic)
  → Repository Layer (MySQL or InfluxDB)
  → Response
```

### 6.3 Analytics Flow

```
Client → POST /analytics/jobs (machine_ids, date_range, analysis_type)
← {job_id: "abc123"}

Background: Celery Worker
  → Fetch telemetry from InfluxDB
  → Run ML model
  → Save results to MinIO
  → Update job status in MySQL

Client → GET /analytics/jobs/{job_id}
← {status: "complete", results: {...}, download_url: "..."}
```

---

## 7. Deployment Architecture

### 7.1 Docker Compose (Development)

All services defined in `docker-compose.yml`:

```yaml
services:
  api, telemetry, rule_engine, analytics_worker,
  reporting_worker, notification_worker, frontend,
  mysql, influxdb, redis, minio, emqx, nginx
```

### 7.2 Production Deployment

Recommended production setup:

- **Orchestration**: Kubernetes (preferred) or Docker Swarm
- **Database**: Managed MySQL (RDS) or self-hosted with replication
- **InfluxDB**: Clustered InfluxDB Enterprise or Cloud
- **Redis**: Redis Sentinel or Redis Cluster
- **MinIO**: Distributed MinIO for object storage redundancy
- **EMQX**: EMQX cluster (2+ nodes)
- **Workers**: Autoscaled Celery workers (HPA in K8s)

### 7.3 Environment Tiers

| Tier | Compose | Kubernetes | Notes |
|---|---|---|---|
| Development | ✓ | | Single machine |
| Staging | ✓ | ✓ | Mirror of prod |
| Production | | ✓ | Full HA setup |

---

## 8. Observability

### 8.1 Logging Strategy

- Structured JSON logs on every service
- Log levels: DEBUG (dev), INFO (staging), WARNING+ (prod)
- Correlation ID (`request_id`) propagated across services
- Log aggregation via Loki + Grafana (recommended)

### 8.2 Metrics

Expose Prometheus-compatible metrics:

| Metric | Service |
|---|---|
| `telemetry_messages_total` | Telemetry Service |
| `telemetry_write_latency_seconds` | Telemetry Service |
| `rule_evaluations_total` | Rule Engine |
| `alert_notifications_sent_total` | Notification Service |
| `api_request_duration_seconds` | API Service |
| `celery_task_duration_seconds` | All workers |

### 8.3 Health Checks

Every service exposes `GET /health` returning:

```json
{
  "status": "healthy",
  "service": "api",
  "dependencies": {
    "mysql": "ok",
    "redis": "ok",
    "influxdb": "ok"
  }
}
```

---

## 9. Scalability Strategy

### 9.1 Horizontal Scaling

| Service | Stateless? | Scale Strategy |
|---|---|---|
| API Service | ✓ | Multiple replicas behind NGINX |
| Telemetry Service | ✓ | Multiple MQTT subscribers (shared group) |
| Celery Workers | ✓ | Auto-scale based on queue depth |
| Frontend | ✓ | CDN + static hosting |

### 9.2 Database Scaling

**MySQL:**
- Read replicas for analytics queries
- Proper indexing on `factory_id`, `device_id`, timestamps
- Connection pooling via SQLAlchemy

**InfluxDB:**
- Retention policies: raw 6 months, aggregated 2 years
- Continuous queries for pre-aggregation
- Bucket-per-factory isolation (optional at scale)

---

## 10. Data Retention Policy

| Data Type | Retention | Storage |
|---|---|---|
| Raw telemetry | 6–12 months | InfluxDB |
| Aggregated telemetry | 2–5 years | InfluxDB (downsampled) |
| Alerts | Permanent | MySQL |
| Analytics results | 30 days | MinIO |
| Generated reports | 90 days | MinIO |
| Audit logs | 1 year | MySQL |
| User data | Until deletion | MySQL |

---

## 11. Failure Recovery

| Failure | Recovery Strategy |
|---|---|
| MQTT disconnect | aiomqtt auto-reconnect with exponential backoff |
| InfluxDB unavailable | Buffer in Redis, replay on reconnect |
| MySQL unavailable | API returns 503; telemetry service continues |
| Celery worker crash | Task auto-retry (max 3 attempts, exponential backoff) |
| API crash | Docker/K8s restart policy |
| Redis unavailable | Celery fallback to database backend |

---

## 12. CI/CD Pipeline

```
Push → GitHub Actions / GitLab CI

Stage 1: Lint & Format
  - ruff (Python)
  - eslint + prettier (JS)

Stage 2: Tests
  - pytest (unit + integration)
  - vitest (frontend)
  - Coverage > 80% required

Stage 3: Build
  - Docker image build
  - Tag with git SHA

Stage 4: Security Scan
  - trivy (container scan)
  - bandit (Python SAST)

Stage 5: Deploy
  - Staging auto-deploy
  - Production manual approval
```

---

## 13. Project Directory Structure

```
factoryops/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers
│   │   ├── core/          # Config, security, dependencies
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── repositories/  # DB access layer
│   │   └── workers/       # Celery tasks
│   ├── tests/
│   ├── alembic/           # DB migrations
│   └── requirements.txt
├── telemetry/
│   ├── main.py            # MQTT subscriber entrypoint
│   ├── handlers/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── stores/
│   │   └── api/
│   └── package.json
├── docker/
│   └── docker-compose.yml
├── nginx/
│   └── nginx.conf
└── docs/
    ├── hld.md
    ├── lld.md
    ├── api-spec.md
    ├── database-schema.md
    └── AGENTS.md
```

---

*End of HLD v2.0*
