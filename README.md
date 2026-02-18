# FactoryOps AI Engineering

**FactoryOps** is a multi-tenant industrial IoT platform for real-time telemetry ingestion, KPI dashboards, rule-based alerting, predictive analytics, and automated reporting. Designed for manufacturing facilities, it provides complete factory isolation, scalable time-series storage, and AI-powered insights.

Built with FastAPI, React, InfluxDB, and Celery, FactoryOps enables factories to monitor machine health, detect anomalies, forecast failures, and generate compliance reports—all from a single, secure platform.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FACTORYOPS PLATFORM                            │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Machines   │──────▶│ MQTT Broker  │──────▶│  Telemetry   │
│  (IoT Edge)  │      │  (Eclipse)   │      │   Service    │
└──────────────┘      └──────────────┘      └──────┬───────┘
                                                    │
                            ┌───────────────────────┼───────────────────────┐
                            │                       │                       │
                            ▼                       ▼                       ▼
                    ┌──────────────┐        ┌──────────────┐      ┌──────────────┐
                    │   InfluxDB   │◀───────│    MySQL     │      │    Redis     │
                    │ (Time-series)│        │  (Metadata)  │      │   (Cache)    │
                    └──────────────┘        └──────────────┘      └──────────────┘
                            ▲                       ▲                       ▲
                            │                       │                       │
                    ┌───────┴───────────────────────┴───────────────────────┘
                    │
            ┌───────▼────────┐          ┌──────────────┐          ┌──────────────┐
            │  FastAPI Backend│◀─────────│    Celery    │◀─────────│   RabbitMQ   │
            │  (REST API)     │          │   Workers    │          │  (Message Q) │
            └────────┬────────┘          └──────┬───────┘          └──────────────┘
                     │                          │
                     │                          ├─▶ Rule Engine (Alerts)
                     │                          ├─▶ Analytics (ML Jobs)
                     │                          ├─▶ Reporting (PDF/Excel)
                     │                          └─▶ Notifications (Email/SMS)
                     │
            ┌────────▼────────┐          ┌──────────────┐
            │  React Frontend │          │    MinIO     │
            │  (Dashboard)    │◀─────────│ (S3 Storage) │
            └─────────────────┘          └──────────────┘
                                         (Reports, Analytics)

┌─────────────────────────────────────────────────────────────────────────┐
│                      FACTORY ISOLATION (JWT)                             │
│  Every API request, DB query, and Celery task enforces factory_id       │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **Factory Isolation**: Multi-tenant by design. Every query filters by `factory_id` from JWT.
- **Schema-Free Telemetry**: InfluxDB stores all metrics without hardcoded parameters.
- **Async Pipeline**: MQTT → Telemetry → InfluxDB → Celery (non-blocking, never raises).
- **Production-Grade**: Structured logging, Prometheus metrics, horizontal scalability.

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- (Optional) Python 3.11+ and Node.js 18+ for local development

### 1. Clone Repository
```bash
git clone https://github.com/your-org/factoryops.git
cd factoryops
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env to customize database passwords, JWT secret, etc.
```

### 3. Start Services
```bash
docker compose up --build -d
```

This starts:
- **FastAPI Backend** on `http://localhost:8000`
- **React Frontend** on `http://localhost:3000`
- **MQTT Broker** on `localhost:1883`
- **InfluxDB** on `localhost:8086`
- **MySQL** on `localhost:3306`
- **Redis** on `localhost:6379`
- **RabbitMQ** on `localhost:5672` (management UI on `15672`)
- **MinIO** on `localhost:9000` (console on `9001`)

### 4. Seed Database
```bash
docker compose exec api python scripts/seed.py
```

This creates:
- Factory: "VPC Industries" (slug: `vpc`)
- Super Admin: `admin@vpc.com` / `Admin@123`
- Sample devices and rules

### 5. Access the Platform
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/docs
- **Prometheus Metrics**: http://localhost:8000/api/v1/metrics

**Login:**
- Email: `admin@vpc.com`
- Password: `Admin@123`

---

## Publish Test Telemetry

### Using mosquitto_pub (CLI)
```bash
mosquitto_pub -h localhost -p 1883 \
  -t "factories/vpc/devices/M01/telemetry" \
  -m '{"metrics":{"voltage":231.4,"current":3.2,"power":745.6,"frequency":50.01,"temperature":72.3}}'
```

### Using Python MQTT Client
```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.connect("localhost", 1883, 60)

payload = {
    "metrics": {
        "voltage": 231.4,
        "current": 3.2,
        "power": 745.6,
        "frequency": 50.01,
        "temperature": 72.3
    }
}

client.publish(
    "factories/vpc/devices/M01/telemetry",
    json.dumps(payload)
)
client.disconnect()
```

Within seconds, you'll see:
- Device auto-registered in the Machines page
- Parameters discovered and available for KPI selection
- Real-time data in dashboards
- Rules evaluated (if configured)

---

## Default Credentials

| Role         | Email              | Password    |
|--------------|-------------------|-------------|
| Super Admin  | admin@vpc.com     | Admin@123   |

**Change these immediately in production!**

---

## API Documentation

### Interactive API Docs
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Authentication
All API endpoints (except `/auth/login` and `/metrics`) require a JWT token:

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@vpc.com","password":"Admin@123"}'

# Returns: {"access_token": "eyJ...", "token_type": "bearer"}

# Use token in subsequent requests
curl http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer eyJ..."
```

### Key Endpoints
- `POST /api/v1/auth/login` - Authenticate and get JWT
- `GET /api/v1/dashboard/summary` - Factory overview
- `GET /api/v1/devices` - List devices
- `GET /api/v1/devices/{id}/kpis/live` - Real-time KPIs
- `GET /api/v1/devices/{id}/kpis/history` - Historical data
- `POST /api/v1/rules` - Create alert rule
- `GET /api/v1/alerts` - List alerts
- `POST /api/v1/analytics/jobs` - Start ML analytics
- `POST /api/v1/reports` - Generate PDF/Excel report
- `GET /api/v1/metrics` - Prometheus metrics

---

## Running Tests

### All Tests
```bash
docker compose exec api pytest tests/ -v
```

### Unit Tests Only
```bash
docker compose exec api pytest tests/unit/ -v
```

### Integration Tests (Factory Isolation)
```bash
docker compose exec api pytest tests/integration/test_factory_isolation.py -v
```

### E2E Test (Full Flow)
```bash
docker compose exec api pytest tests/e2e/test_full_flow.py -v
```

Expected output: All 6 factory isolation tests and 30 unit tests should pass.

---

## Features

### 1. Real-Time Telemetry Ingestion
- MQTT-based telemetry from IoT devices
- Schema-free: any metric name/value accepted
- Auto-discovery of new parameters
- Batched writes to InfluxDB for performance

### 2. Dynamic KPI Dashboards
- Live values with last-seen timestamps
- Historical charts (hourly, daily, weekly aggregations)
- Per-device parameter selection
- Responsive UI with Recharts visualizations

### 3. Rule-Based Alerting
- Visual rule builder with AND/OR logic
- Severity levels (low, medium, high, critical)
- Cooldown periods to prevent alert storms
- Scheduled rules (time windows, date ranges)
- Multi-channel notifications (email, WhatsApp)

### 4. Predictive Analytics
- Anomaly detection (Isolation Forest)
- Forecasting (Prophet time-series)
- Custom model training with hyperparameter tuning
- Results stored in MinIO for download

### 5. Automated Reporting
- PDF reports with charts and tables
- Excel workbooks with multiple sheets
- JSON exports for API integration
- Scheduled generation via Celery
- S3-compatible storage with presigned URLs

### 6. User Management
- Multi-user support with invite workflow
- Role-based access (super_admin, admin)
- Granular permissions (rules, analytics, reports)
- Token-based invite links (48h expiry)

### 7. Observability
- Structured JSON logging (structlog)
- Prometheus metrics endpoint
- Request tracing with X-Request-ID
- Celery task monitoring

---

## Production Deployment

### Environment Variables
Key settings in `.env`:

```bash
# Database
MYSQL_HOST=mysql
MYSQL_PASSWORD=<strong-password>

# JWT
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256

# MQTT
MQTT_BROKER_HOST=mqtt
MQTT_USERNAME=factoryops
MQTT_PASSWORD=<strong-password>

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=<generate-from-influxdb-ui>

# MinIO
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>

# Optional: Notifications
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=<app-password>

TWILIO_ACCOUNT_SID=<your-sid>
TWILIO_AUTH_TOKEN=<your-token>
```

### Security Checklist
- [ ] Change all default passwords
- [ ] Generate strong JWT secret (`openssl rand -hex 32`)
- [ ] Enable HTTPS with SSL certificates (nginx reverse proxy)
- [ ] Configure firewall rules (only expose 80/443)
- [ ] Set up database backups (MySQL + InfluxDB)
- [ ] Enable SMTP/Twilio for production notifications
- [ ] Review and update CORS settings in `main.py`
- [ ] Set up Prometheus + Grafana for monitoring
- [ ] Configure log aggregation (ELK stack or CloudWatch)

### Scaling Recommendations
- **Horizontal**: Run multiple API/worker containers behind load balancer
- **InfluxDB**: Use InfluxDB Enterprise or Cloud for clustering
- **MySQL**: Master-replica setup with ProxySQL
- **Celery**: Separate workers by queue (rule_engine, analytics, reporting)
- **Redis**: Redis Sentinel for high availability

---

## Development

### Local Development (without Docker)

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start services (MySQL, InfluxDB, Redis, RabbitMQ, MQTT)
# Then:
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Telemetry Service
```bash
cd telemetry
pip install -r requirements.txt
python main.py
```

#### Celery Workers
```bash
cd backend
celery -A app.workers.celery_app worker -Q rule_engine,analytics,reporting,notifications --loglevel=info
```

---

## Project Structure

```
factoryops/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── core/           # Config, database, security
│   │   ├── models/         # SQLAlchemy models
│   │   ├── repositories/   # Data access layer
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── workers/        # Celery tasks
│   ├── alembic/            # Database migrations
│   ├── scripts/            # Seed data, utilities
│   └── tests/              # Unit, integration, E2E tests
├── frontend/               # React frontend
│   ├── src/
│   │   ├── api/            # API client
│   │   ├── components/     # Reusable components
│   │   ├── hooks/          # React hooks
│   │   ├── pages/          # Page components
│   │   ├── stores/         # Zustand state management
│   │   └── types/          # TypeScript types
├── telemetry/              # MQTT telemetry service
│   ├── handlers/           # Ingestion, InfluxDB, cache
│   └── main.py             # MQTT subscriber loop
├── docker/                 # Docker Compose config
├── docs/                   # Architecture documentation
│   ├── hld_enhanced.md     # High-level design
│   ├── lld_enhanced.md     # Low-level design
│   └── api-spec.md         # API specification
└── .env.example            # Environment template
```

---

## Troubleshooting

### Telemetry Not Appearing
1. Check MQTT connection: `docker compose logs mqtt`
2. Verify telemetry service: `docker compose logs telemetry`
3. Check topic format: `factories/{factory_slug}/devices/{device_key}/telemetry`
4. Verify InfluxDB: `docker compose exec influxdb influx`

### Rules Not Triggering
1. Ensure rule is active
2. Check device_ids match
3. Verify parameter names in conditions
4. Check Celery worker: `docker compose logs worker`
5. Review cooldown settings

### Analytics Job Stuck
1. Check worker logs: `docker compose logs worker`
2. Verify sufficient data in InfluxDB
3. Check job status in database or UI
4. Retry failed jobs from UI

### Login Issues
1. Verify seed script ran: `docker compose exec api python scripts/seed.py`
2. Check database: `docker compose exec mysql mysql -u root -p`
3. Reset password via direct DB update if needed

---

## Contributing

### Code Style
- **Backend**: Black formatter, isort for imports
- **Frontend**: ESLint + Prettier
- **Commits**: Conventional Commits format

### Pull Request Process
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m "feat: add amazing feature"`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request with description

### Testing Requirements
- All new features must include tests
- Factory isolation tests must pass
- E2E test should cover new workflows

---

## License

MIT License - see LICENSE file for details

---

## Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues
- **Security**: Report vulnerabilities to security@factoryops.io

---

**Built with ❤️ for industrial IoT and predictive maintenance.**
