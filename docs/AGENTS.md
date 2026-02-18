# AGENTS.md
## FactoryOps AI Engineering — Claude Code Implementation Guide
### Read this file first before writing any code

---

## 0. Project Identity

You are implementing **FactoryOps AI Engineering** — a multi-tenant industrial energy intelligence platform. This is a **production system** for real factories. Treat every decision accordingly.

**Tech stack at a glance:**
- Backend: **Python 3.11 + FastAPI** (async)
- Frontend: **React 18 + Vite + Tailwind CSS**
- Metadata DB: **MySQL 8** via SQLAlchemy 2.0 (async)
- Time-series DB: **InfluxDB 2.x**
- Task queue: **Celery + Redis**
- MQTT: **EMQX broker** via aiomqtt
- Object storage: **MinIO**
- Containerized: **Docker Compose**

---

## 1. Non-Negotiable Rules

### 1.1 Factory Isolation

**Every single database query must filter by `factory_id`.** There are no exceptions.

```python
# ✅ CORRECT
devices = await db.execute(
    select(Device).where(Device.factory_id == factory_id, Device.id == device_id)
)

# ❌ WRONG — missing factory_id filter
devices = await db.execute(select(Device).where(Device.id == device_id))
```

**Every FastAPI route that touches data must extract `factory_id` from the JWT.** Use the dependency:

```python
@router.get("/devices/{device_id}")
async def get_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # current_user.factory_id is always present — use it
    device = await device_service.get_device(db, current_user.factory_id, device_id)
```

### 1.2 Async Everywhere in Backend

All backend code must use `async def`. Never use sync blocking calls inside async functions.

```python
# ✅ CORRECT
async def get_factory(db: AsyncSession, factory_id: int) -> Factory:
    result = await db.execute(select(Factory).where(Factory.id == factory_id))
    return result.scalar_one_or_none()

# ❌ WRONG — blocking call inside async
def get_factory(db: Session, factory_id: int):
    return db.query(Factory).filter(Factory.id == factory_id).first()
```

### 1.3 Never Hardcode KPI Parameters

The system must NEVER have a hardcoded list of telemetry parameters. Parameters are always discovered dynamically from the `device_parameters` table.

```python
# ✅ CORRECT — fetch from DB
kpi_params = await get_selected_parameters(db, factory_id, device_id)

# ❌ WRONG — hardcoded list
kpi_params = ["voltage", "current", "power", "frequency"]
```

### 1.4 Telemetry Pipeline Must Never Crash

The MQTT subscriber loop must catch all exceptions per message. A bad payload from one device must not affect any other device.

```python
async def on_message(message):
    try:
        await process_telemetry(message.topic, message.payload)
    except Exception as e:
        logger.error("Telemetry error", error=str(e), topic=str(message.topic))
    # DO NOT re-raise
```

### 1.5 Celery Tasks for Heavy Work

**Never** run ML computation, report generation, or bulk InfluxDB queries inside a FastAPI endpoint. Always dispatch a Celery task and return a job ID.

---

## 2. Project Structure

```
factoryops/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app factory
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── dashboard.py
│   │   │   │   ├── devices.py
│   │   │   │   ├── telemetry.py
│   │   │   │   ├── rules.py
│   │   │   │   ├── alerts.py
│   │   │   │   ├── analytics.py
│   │   │   │   ├── reports.py
│   │   │   │   └── users.py
│   │   ├── core/
│   │   │   ├── config.py         # Settings from env vars
│   │   │   ├── security.py       # JWT encode/decode
│   │   │   ├── dependencies.py   # FastAPI Depends (get_db, get_current_user)
│   │   │   └── logging.py        # Structured JSON logger
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── factory.py
│   │   │   ├── user.py
│   │   │   ├── device.py
│   │   │   ├── device_parameter.py
│   │   │   ├── rule.py
│   │   │   ├── alert.py
│   │   │   └── analytics_job.py
│   │   ├── schemas/              # Pydantic request/response models
│   │   ├── services/             # Business logic
│   │   ├── repositories/         # DB query layer
│   │   └── workers/
│   │       ├── celery_app.py
│   │       ├── rule_engine.py
│   │       ├── analytics.py
│   │       ├── reporting.py
│   │       └── notifications.py
│   ├── alembic/                  # DB migrations
│   ├── tests/
│   └── requirements.txt
├── telemetry/
│   ├── main.py                   # Entrypoint
│   ├── subscriber.py             # MQTT client
│   ├── handlers/
│   │   ├── ingestion.py          # Core ingestion logic
│   │   └── parameter_discovery.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                  # Axios client + endpoint functions
│   │   ├── components/
│   │   │   ├── ui/               # Reusable components
│   │   │   ├── kpi/              # KPICard, KPICardGrid
│   │   │   ├── charts/           # TelemetryChart, AggregationSelector
│   │   │   └── rules/            # RuleBuilder, ConditionEditor
│   │   ├── pages/
│   │   │   ├── FactorySelect.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Machines.tsx
│   │   │   ├── DeviceDetail.tsx
│   │   │   ├── Rules.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── Reports.tsx
│   │   │   └── Users.tsx
│   │   ├── hooks/                # React Query hooks
│   │   ├── stores/               # Zustand stores
│   │   └── types/                # TypeScript types
│   └── package.json
└── docker/
    └── docker-compose.yml
```

---

## 3. Implementation Order (Priority Queue)

Implement in this exact order. Do not start a later step before a prior step is complete and tested.

### Phase 1 — Infrastructure & Auth
1. Docker Compose with all services (MySQL, InfluxDB, Redis, MinIO, EMQX, API, Telemetry, Frontend)
2. MySQL schema + Alembic migrations (all tables from LLD section 2)
3. FastAPI app skeleton with health check
4. JWT auth: login, token validation, `get_current_user` dependency
5. Factory selector API (`GET /api/v1/factories`)

### Phase 2 — Core Telemetry
6. Telemetry Ingestion Service (MQTT subscriber + InfluxDB write)
7. Dynamic parameter discovery (auto-upsert to `device_parameters`)
8. Device management API (CRUD)
9. KPI live endpoint (`GET /devices/{id}/kpis/live`)
10. KPI history endpoint (`GET /devices/{id}/kpis/history`)

### Phase 3 — Rules & Alerts
11. Rule CRUD API
12. Rule engine Celery task
13. Condition evaluator (support AND/OR trees)
14. Cooldown management
15. Alert creation + listing API
16. Notification Celery task (email + WhatsApp)

### Phase 4 — Dashboard & Frontend
17. Dashboard summary API
18. React app skeleton + routing + Tailwind setup
19. Factory select page → Login page
20. Dashboard page (summary cards)
21. Machines list page
22. Device detail page (KPI cards + live chart)
23. Rules page + Rule builder
24. Alerts panel

### Phase 5 — Analytics & Reporting
25. Analytics job API + Celery worker
26. Anomaly detection (Isolation Forest)
27. Energy forecasting (Prophet)
28. Report generation (PDF + Excel)
29. Analytics & Reports pages in frontend

### Phase 6 — Users & Polish
30. User management API (invite + permissions)
31. Users page (super_admin only)
32. Observability (structured logging, metrics endpoint)
33. CI pipeline config

---

## 4. API Conventions

### 4.1 Base URL Structure

All API endpoints: `/api/v1/{resource}`

### 4.2 Authentication Header

```
Authorization: Bearer <jwt_token>
```

### 4.3 Response Envelope (lists)

```json
{
  "data": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### 4.4 Response Envelope (single)

```json
{
  "data": { ... }
}
```

### 4.5 Error Response

```json
{
  "error": {
    "code": "DEVICE_NOT_FOUND",
    "message": "Human-readable message"
  }
}
```

### 4.6 Pagination Query Params

All list endpoints accept: `?page=1&per_page=20`

---

## 5. FastAPI Patterns

### 5.1 Route File Structure

```python
# app/api/v1/devices.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, get_db
from app.services.device_service import DeviceService
from app.schemas.device import DeviceCreate, DeviceResponse

router = APIRouter(prefix="/devices", tags=["devices"])

@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: DeviceService = Depends(),
):
    devices = await service.list_devices(db, current_user.factory_id)
    return devices
```

### 5.2 Dependency Injection

```python
# app/core/dependencies.py
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_jwt(token)
    user = await get_user_by_id(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401)
    return user

def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin only")
    return user
```

### 5.3 Service Layer Pattern

```python
# app/services/device_service.py
class DeviceService:
    async def get_device(
        self, db: AsyncSession, factory_id: int, device_id: int
    ) -> Device:
        device = await device_repo.get_by_factory_and_id(db, factory_id, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return device
```

---

## 6. SQLAlchemy Patterns

### 6.1 Model Base

```python
# app/models/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### 6.2 Async Session

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### 6.3 InfluxDB Client

```python
# app/core/influx.py
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

influx_client = InfluxDBClientAsync(
    url=settings.INFLUXDB_URL,
    token=settings.INFLUXDB_TOKEN,
    org=settings.INFLUXDB_ORG,
)

async def get_write_api():
    return influx_client.write_api()

async def get_query_api():
    return influx_client.query_api()
```

---

## 7. Frontend Patterns

### 7.1 API Client

```typescript
// src/api/client.ts
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

const api = axios.create({ baseURL: '/api/v1' });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  }
);
```

### 7.2 React Query Hook Pattern

```typescript
// src/hooks/useKPIsLive.ts
export function useKPIsLive(deviceId: number) {
  return useQuery({
    queryKey: ['kpis', 'live', deviceId],
    queryFn: () => api.get(`/devices/${deviceId}/kpis/live`).then(r => r.data.data),
    refetchInterval: 5000,
    staleTime: 3000,
  });
}
```

### 7.3 Protected Routes

```typescript
// src/components/ProtectedRoute.tsx
export function ProtectedRoute({ children, requireSuperAdmin = false }) {
  const { user } = useAuthStore();
  if (!user) return <Navigate to="/login" />;
  if (requireSuperAdmin && user.role !== 'super_admin') return <Navigate to="/dashboard" />;
  return children;
}
```

---

## 8. Docker Compose Reference

```yaml
# docker-compose.yml (development)
version: '3.9'
services:

  api:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [mysql, redis, influxdb, minio]
    volumes: [./backend:/app]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  telemetry:
    build: ./telemetry
    env_file: .env
    depends_on: [emqx, influxdb, mysql, redis]

  rule_engine:
    build: ./backend
    command: celery -A app.workers.celery_app worker -Q rule_engine --loglevel=info
    env_file: .env
    depends_on: [redis, mysql]

  analytics_worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker -Q analytics --loglevel=info
    env_file: .env

  reporting_worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker -Q reporting --loglevel=info
    env_file: .env

  notification_worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker -Q notifications --loglevel=info
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    volumes: [./frontend:/app]
    command: npm run dev -- --host

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: factoryops
      MYSQL_USER: factoryops
      MYSQL_PASSWORD: secret
    ports: ["3306:3306"]
    volumes: [mysql_data:/var/lib/mysql]

  influxdb:
    image: influxdb:2.7
    ports: ["8086:8086"]
    volumes: [influxdb_data:/var/lib/influxdb2]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    volumes: [minio_data:/data]

  emqx:
    image: emqx:5
    ports: ["1883:1883", "8083:8083", "18083:18083"]

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes: [./nginx/nginx.conf:/etc/nginx/nginx.conf]
    depends_on: [api, frontend]

volumes:
  mysql_data:
  influxdb_data:
  minio_data:
```

---

## 9. Testing Requirements

Every feature must have tests before it is considered complete.

### 9.1 Backend Tests

```
tests/
├── unit/
│   ├── test_rule_evaluator.py    # Test condition evaluation logic
│   ├── test_parameter_discovery.py
│   └── test_jwt.py
├── integration/
│   ├── test_auth.py              # Full login → token flow
│   ├── test_devices.py           # CRUD + factory isolation
│   ├── test_telemetry.py         # Ingestion pipeline
│   ├── test_rules.py             # Rule creation + evaluation
│   └── test_factory_isolation.py # Critical: cross-factory access = 403
└── conftest.py                    # Test DB, fixtures
```

### 9.2 Factory Isolation Test (Mandatory)

```python
async def test_cross_factory_access_denied(client, factory_a_token, factory_b_device):
    """Factory A user must NOT access Factory B's device."""
    response = await client.get(
        f"/api/v1/devices/{factory_b_device.id}",
        headers={"Authorization": f"Bearer {factory_a_token}"},
    )
    assert response.status_code == 404  # Not 403 — don't reveal existence
```

---

## 10. Logging Standard

Every log statement must be structured JSON. Use a logger configured for this:

```python
import structlog

logger = structlog.get_logger()

# Usage
logger.info("telemetry.received", factory_id=factory_id, device_id=device_id,
            parameter_count=len(metrics))
logger.error("telemetry.write_failed", factory_id=factory_id, error=str(e))
```

**Mandatory log fields:**
- `factory_id` on all logs where applicable
- `device_id` on all telemetry logs
- `user_id` on all API logs
- `request_id` (generated per request via middleware)

---

## 11. Common Pitfalls to Avoid

| Pitfall | Correct Approach |
|---|---|
| Blocking calls in async functions | Use `await` or `asyncio.to_thread()` |
| Hardcoding parameter names | Always query `device_parameters` table |
| Missing `factory_id` filter | Add to every DB query |
| Returning 403 for cross-factory access | Return 404 (don't reveal resource existence) |
| Running ML in FastAPI endpoint | Always use Celery task |
| Writing raw SQL without factory filter | Use ORM with factory_id always |
| Starting InfluxDB query without tags | Always include `factory_id` tag filter |
| Raising exceptions in MQTT handler | Catch all, log, continue |
| Synchronous Celery in telemetry path | Dispatch task with `.delay()`, never `.apply_sync()` |

---

## 12. Quick Reference: Key Data Flows

### Telemetry Arrives:
```
EMQX → aiomqtt subscriber → validate payload → upsert device_parameters (MySQL)
→ batch write device_metrics (InfluxDB) → update device.last_seen (MySQL)
→ evaluate_rules_task.delay() [non-blocking]
```

### User Views Device Dashboard:
```
GET /devices/{id}/kpis/live → fetch selected params from MySQL
→ query InfluxDB last() for each param → return KPI cards data
GET /devices/{id}/kpis/history → query InfluxDB aggregateWindow → return chart data
```

### Rule Triggers Alert:
```
evaluate_rules_task() → check cooldown (MySQL) → evaluate conditions
→ INSERT alert (MySQL) → upsert cooldown (MySQL)
→ send_notifications_task.delay() → email/WhatsApp via configured channels
```

### Analytics Requested:
```
POST /analytics/jobs → INSERT job (MySQL, status=pending) → run_analytics_job.delay()
← {job_id}
[background] Celery → fetch InfluxDB data → run ML → save to MinIO → UPDATE job status=complete
GET /analytics/jobs/{id} → return status + result_url
```

---

*This file is the source of truth for all implementation decisions. When in doubt, refer here before writing code.*
