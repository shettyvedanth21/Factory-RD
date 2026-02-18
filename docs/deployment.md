# FactoryOps Production Deployment Guide

This guide covers deploying FactoryOps to production with best practices for security, reliability, and scalability.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Initial Deployment](#initial-deployment)
4. [SSL/TLS Certificate Setup](#ssltls-certificate-setup)
5. [Database Migrations](#database-migrations)
6. [Update & Rollout Procedure](#update--rollout-procedure)
7. [Backup & Restore](#backup--restore)
8. [Monitoring Setup](#monitoring-setup)
9. [Scaling Guide](#scaling-guide)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements

**Minimum (for small deployments, <10 devices):**
- 4 CPU cores
- 8 GB RAM
- 100 GB SSD storage
- 10 Mbps network

**Recommended (for production, 10-100 devices):**
- 8 CPU cores
- 16 GB RAM
- 500 GB SSD storage (InfluxDB grows with telemetry volume)
- 100 Mbps network

**High-scale (100+ devices):**
- 16+ CPU cores
- 32+ GB RAM
- 1 TB+ SSD storage
- 1 Gbps network
- Consider clustering InfluxDB and MySQL

### Software Requirements

- **OS**: Ubuntu 22.04 LTS or CentOS 8+ (recommended)
- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Domain name** with DNS A record pointing to server
- **SSL Certificate** (Let's Encrypt recommended)
- **Firewall**: Allow ports 80, 443, 1883 (MQTT)

### Optional

- Prometheus + Grafana for monitoring
- Log aggregation (ELK stack or CloudWatch)
- Backup storage (AWS S3, Google Cloud Storage)

---

## Environment Configuration

### 1. Clone Repository

```bash
git clone https://github.com/your-org/factoryops.git
cd factoryops
```

### 2. Create Environment File

```bash
cp .env.example .env.production
```

### 3. Configure Environment Variables

Edit `.env.production`:

```bash
# CRITICAL: Change all default values for production!

# Application
ENVIRONMENT=production
APP_URL=https://your-domain.com

# MySQL
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=factoryops
MYSQL_USER=factoryops
MYSQL_PASSWORD=<GENERATE_STRONG_PASSWORD>  # openssl rand -base64 32
MYSQL_ROOT_PASSWORD=<GENERATE_STRONG_PASSWORD>

# JWT Authentication
JWT_SECRET_KEY=<GENERATE_SECRET>  # openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=factoryops
INFLUXDB_BUCKET=factoryops
INFLUXDB_TOKEN=<GENERATE_TOKEN>  # openssl rand -base64 32
INFLUXDB_ADMIN_PASSWORD=<GENERATE_PASSWORD>

# MinIO (S3-compatible storage)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<GENERATE_ACCESS_KEY>  # 20 chars alphanumeric
MINIO_SECRET_KEY=<GENERATE_SECRET_KEY>  # openssl rand -base64 32
MINIO_BUCKET=factoryops
MINIO_BACKUP_BUCKET=factoryops-backups

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=factoryops
RABBITMQ_PASSWORD=<GENERATE_PASSWORD>

# MQTT
MQTT_BROKER_HOST=mqtt
MQTT_BROKER_PORT=1883
MQTT_USERNAME=factoryops
MQTT_PASSWORD=<GENERATE_PASSWORD>

# SMTP (Email Notifications) - Optional
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=<APP_PASSWORD>
SMTP_FROM=noreply@your-domain.com

# Twilio (WhatsApp Notifications) - Optional
TWILIO_ACCOUNT_SID=<YOUR_SID>
TWILIO_AUTH_TOKEN=<YOUR_TOKEN>
TWILIO_WHATSAPP_FROM=+14155238886

# GitHub Container Registry (for pulling images)
GITHUB_REPOSITORY=your-org/factoryops
IMAGE_TAG=latest  # or specific SHA for pinned deployments
```

### 4. Create Docker Secrets

For production, use Docker secrets instead of environment files:

```bash
# Create secrets
echo "your_mysql_password" | docker secret create mysql_password -
echo "your_mysql_root_password" | docker secret create mysql_root_password -
echo "your_jwt_secret" | docker secret create jwt_secret -
echo "your_influxdb_token" | docker secret create influxdb_token -
echo "your_influxdb_admin_password" | docker secret create influxdb_admin_password -
echo "your_rabbitmq_password" | docker secret create rabbitmq_password -
echo "your_minio_secret_key" | docker secret create minio_secret_key -
```

Verify secrets:

```bash
docker secret ls
```

---

## Initial Deployment

### 1. Pull Docker Images

Login to GitHub Container Registry:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
```

Pull images:

```bash
export GITHUB_REPOSITORY=your-org/factoryops
export IMAGE_TAG=latest

docker pull ghcr.io/$GITHUB_REPOSITORY/api:$IMAGE_TAG
docker pull ghcr.io/$GITHUB_REPOSITORY/telemetry:$IMAGE_TAG
docker pull ghcr.io/$GITHUB_REPOSITORY/frontend:$IMAGE_TAG
```

### 2. Start Infrastructure Services

Start databases first:

```bash
docker compose -f docker/docker-compose.prod.yml up -d mysql redis influxdb rabbitmq minio mqtt
```

Wait for services to be healthy (check logs):

```bash
docker compose -f docker/docker-compose.prod.yml ps
docker compose -f docker/docker-compose.prod.yml logs -f mysql
```

### 3. Run Database Migrations

```bash
docker compose -f docker/docker-compose.prod.yml run --rm api alembic upgrade head
```

### 4. Seed Initial Data

```bash
docker compose -f docker/docker-compose.prod.yml run --rm api python scripts/seed.py
```

This creates:
- Default factory: "VPC Industries" (slug: `vpc`)
- Super admin user: `admin@vpc.com` / `Admin@123`

**CRITICAL: Change the default password immediately after first login!**

### 5. Start Application Services

```bash
docker compose -f docker/docker-compose.prod.yml up -d api telemetry worker frontend nginx
```

### 6. Verify Deployment

Check all services are running:

```bash
docker compose -f docker/docker-compose.prod.yml ps
```

Expected output: All services should show `Up` and `(healthy)`.

Test endpoints:

```bash
# Health check
curl http://localhost/health

# API docs
curl http://localhost/api/docs

# Frontend
curl -I http://localhost/
```

---

## SSL/TLS Certificate Setup

### Option 1: Let's Encrypt (Recommended)

Install Certbot:

```bash
sudo apt-get update
sudo apt-get install certbot
```

Obtain certificate:

```bash
sudo certbot certonly --standalone -d your-domain.com
```

Certificates will be saved to:
- `/etc/letsencrypt/live/your-domain.com/fullchain.pem`
- `/etc/letsencrypt/live/your-domain.com/privkey.pem`

Create symbolic links:

```bash
sudo mkdir -p nginx/ssl
sudo ln -s /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/fullchain.pem
sudo ln -s /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/privkey.pem
```

Set up auto-renewal:

```bash
sudo crontab -e
# Add line:
0 3 * * 1 certbot renew --quiet && docker compose -f /path/to/docker/docker-compose.prod.yml restart nginx
```

### Option 2: Self-Signed Certificate (Development Only)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/CN=your-domain.com"
```

### Restart NGINX

```bash
docker compose -f docker/docker-compose.prod.yml restart nginx
```

Verify HTTPS:

```bash
curl -I https://your-domain.com
```

---

## Database Migrations

### Running Migrations

Always run migrations before deploying new application versions:

```bash
# Stop API and workers (keeps DB running)
docker compose -f docker/docker-compose.prod.yml stop api worker

# Run migrations
docker compose -f docker/docker-compose.prod.yml run --rm api alembic upgrade head

# Restart services
docker compose -f docker/docker-compose.prod.yml up -d api worker
```

### Rollback Migration

If a migration fails:

```bash
# Rollback one version
docker compose -f docker/docker-compose.prod.yml run --rm api alembic downgrade -1

# Rollback to specific revision
docker compose -f docker/docker-compose.prod.yml run --rm api alembic downgrade <revision_id>
```

### Check Current Migration Version

```bash
docker compose -f docker/docker-compose.prod.yml run --rm api alembic current
```

---

## Update & Rollout Procedure

### Zero-Downtime Rolling Update

1. **Pull new images:**

```bash
export IMAGE_TAG=abc123  # Use specific SHA for rollback capability
docker pull ghcr.io/$GITHUB_REPOSITORY/api:$IMAGE_TAG
docker pull ghcr.io/$GITHUB_REPOSITORY/telemetry:$IMAGE_TAG
docker pull ghcr.io/$GITHUB_REPOSITORY/frontend:$IMAGE_TAG
```

2. **Update docker-compose file:**

```bash
# Update IMAGE_TAG in .env.production
echo "IMAGE_TAG=$IMAGE_TAG" >> .env.production
```

3. **Run migrations (if any):**

```bash
docker compose -f docker/docker-compose.prod.yml stop api worker
docker compose -f docker/docker-compose.prod.yml run --rm api alembic upgrade head
```

4. **Rolling restart:**

```bash
# Update API (scale to 2 replicas for zero downtime)
docker compose -f docker/docker-compose.prod.yml up -d --scale api=2 --no-recreate api

# Wait for new instances to be healthy
sleep 30

# Remove old instances
docker compose -f docker/docker-compose.prod.yml up -d --scale api=1 api

# Update worker
docker compose -f docker/docker-compose.prod.yml up -d worker

# Update telemetry
docker compose -f docker/docker-compose.prod.yml up -d telemetry

# Update frontend
docker compose -f docker/docker-compose.prod.yml up -d frontend
```

5. **Verify deployment:**

```bash
# Check logs
docker compose -f docker/docker-compose.prod.yml logs -f api

# Test endpoints
curl https://your-domain.com/health
```

### Rollback Procedure

If issues occur:

```bash
# Revert to previous image tag
export IMAGE_TAG=previous-sha
echo "IMAGE_TAG=$IMAGE_TAG" >> .env.production

# Rollback migration if necessary
docker compose -f docker/docker-compose.prod.yml run --rm api alembic downgrade -1

# Restart services
docker compose -f docker/docker-compose.prod.yml up -d api worker telemetry frontend
```

---

## Backup & Restore

### Automated Backups

The backup script is located at `scripts/backup.sh`.

**Setup cron job:**

```bash
sudo crontab -e
```

Add:

```cron
# Daily backup at 2 AM
0 2 * * * cd /path/to/factoryops && ./scripts/backup.sh >> /var/log/factoryops-backup.log 2>&1

# Weekly verification (Sundays at 3 AM)
0 3 * * 0 cd /path/to/factoryops && ./scripts/verify-backup.sh >> /var/log/factoryops-backup-verify.log 2>&1
```

**Manual backup:**

```bash
./scripts/backup.sh
```

Backups are stored in:
- Local: `/tmp/factoryops-backups/`
- MinIO: `s3://factoryops-backups/mysql/` and `s3://factoryops-backups/influxdb/`

### Restore from Backup

**MySQL restore:**

```bash
# List available backups
mc ls factoryops-minio/factoryops-backups/mysql/

# Download backup
mc cp factoryops-minio/factoryops-backups/mysql/mysql_20240219_020000.sql.gz /tmp/

# Stop API and workers
docker compose -f docker/docker-compose.prod.yml stop api worker

# Restore database
gunzip < /tmp/mysql_20240219_020000.sql.gz | \
  docker compose -f docker/docker-compose.prod.yml exec -T mysql \
  mysql -u factoryops -p"$MYSQL_PASSWORD" factoryops

# Restart services
docker compose -f docker/docker-compose.prod.yml up -d api worker
```

**InfluxDB restore:**

```bash
# Download backup
mc cp factoryops-minio/factoryops-backups/influxdb/influxdb_20240219_020000.tar.gz /tmp/

# Extract
tar -xzf /tmp/influxdb_20240219_020000.tar.gz -C /tmp/

# Stop telemetry service
docker compose -f docker/docker-compose.prod.yml stop telemetry

# Restore
docker compose -f docker/docker-compose.prod.yml exec -T influxdb \
  influx restore \
  --host http://localhost:8086 \
  --token "$INFLUXDB_TOKEN" \
  /tmp/influxdb_20240219_020000

# Restart telemetry
docker compose -f docker/docker-compose.prod.yml up -d telemetry
```

---

## Monitoring Setup

### Prometheus + Grafana

**1. Add to docker-compose.prod.yml:**

```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    restart: always
    networks:
      - factoryops-net

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    restart: always
    networks:
      - factoryops-net
    depends_on:
      - prometheus
```

**2. Create prometheus.yml:**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'factoryops-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/api/v1/metrics'
```

**3. Import Grafana dashboards:**

- FactoryOps system metrics
- Database performance
- Celery task queues
- API request rates

### Log Aggregation

**Using Docker logging driver:**

```bash
# Configure in docker-compose.prod.yml
logging:
  driver: "fluentd"
  options:
    fluentd-address: "fluentd-server:24224"
    tag: "factoryops.{{.Name}}"
```

Or use ELK stack / CloudWatch / Datadog.

### Alerts

Configure alerts in Prometheus:

```yaml
# alerts.yml
groups:
  - name: factoryops
    rules:
      - alert: HighErrorRate
        expr: rate(factoryops_api_request_duration_seconds_count{status_code="500"}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: DatabaseDown
        expr: up{job="mysql"} == 0
        for: 1m
        annotations:
          summary: "MySQL database is down"
```

---

## Scaling Guide

### Horizontal Scaling

**Scale API instances:**

```bash
docker compose -f docker/docker-compose.prod.yml up -d --scale api=4
```

NGINX load balancer will distribute requests automatically.

**Scale Celery workers:**

```bash
# Scale by queue
docker compose -f docker/docker-compose.prod.yml up -d --scale worker=3

# Or separate workers by queue
docker compose -f docker/docker-compose.prod.yml run -d --name worker-rules \
  api celery -A app.workers.celery_app worker -Q rule_engine --concurrency=4

docker compose -f docker/docker-compose.prod.yml run -d --name worker-analytics \
  api celery -A app.workers.celery_app worker -Q analytics --concurrency=2
```

### Vertical Scaling

Update resource limits in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
    reservations:
      cpus: '2.0'
      memory: 2G
```

### Database Scaling

**MySQL:**

- Use ProxySQL for connection pooling
- Set up master-replica replication
- Consider MySQL NDB Cluster for high availability

**InfluxDB:**

- Use InfluxDB Enterprise for clustering
- Or migrate to InfluxDB Cloud for managed service
- Implement data retention policies

**Redis:**

- Use Redis Sentinel for high availability
- Or Redis Cluster for horizontal scaling

---

## Troubleshooting

### Service Won't Start

Check logs:

```bash
docker compose -f docker/docker-compose.prod.yml logs <service-name>
```

Check health:

```bash
docker compose -f docker/docker-compose.prod.yml ps
```

### Database Connection Errors

Verify credentials:

```bash
docker compose -f docker/docker-compose.prod.yml exec mysql \
  mysql -u factoryops -p"$MYSQL_PASSWORD" -e "SELECT 1"
```

Check network:

```bash
docker compose -f docker/docker-compose.prod.yml exec api ping mysql
```

### High Memory Usage

Check container stats:

```bash
docker stats
```

Restart services:

```bash
docker compose -f docker/docker-compose.prod.yml restart <service-name>
```

### Telemetry Not Ingesting

Check MQTT broker:

```bash
docker compose -f docker/docker-compose.prod.yml logs mqtt
```

Test MQTT connection:

```bash
mosquitto_pub -h your-domain.com -p 1883 -u factoryops -P "$MQTT_PASSWORD" \
  -t "factories/vpc/devices/TEST/telemetry" \
  -m '{"metrics":{"voltage":230}}'
```

Check telemetry service logs:

```bash
docker compose -f docker/docker-compose.prod.yml logs -f telemetry
```

### Slow Queries

Check InfluxDB performance:

```bash
docker compose -f docker/docker-compose.prod.yml exec influxdb \
  influx query 'SHOW QUERIES' --org factoryops
```

Check MySQL slow query log:

```bash
docker compose -f docker/docker-compose.prod.yml exec mysql \
  mysql -u root -p"$MYSQL_ROOT_PASSWORD" \
  -e "SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;"
```

---

## Support

For production support:

- **Documentation**: `/docs` directory
- **GitHub Issues**: Report bugs and feature requests
- **Security Issues**: security@factoryops.io
- **Enterprise Support**: enterprise@factoryops.io

---

**Last updated**: February 2024
