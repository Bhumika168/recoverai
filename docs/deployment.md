# RecoverAI Production Deployment Guide

This guide details the complete production architecture, deployment workflows, environment configuration, migration strategies, security controls, backup procedures, and rollback plans for **RecoverAI**.

---

## 1. Stack & Architecture Overview

RecoverAI is architected as a distributed, decoupled multi-tenant SaaS platform:

```
                          ┌────────────────────────┐
                          │   Internet / Traffic   │
                          │   (Cloudflare / CDN)   │
                          └───────────┬────────────┘
                                      │ HTTPS
                 ┌────────────────────┴────────────────────┐
                 │                                         │
                 ▼                                         ▼
   ┌───────────────────────────┐             ┌───────────────────────────┐
   │     Frontend Service      │             │    Backend API Service    │
   │  Next.js 15 (App Router)  │             │   FastAPI / Python 3.12   │
   │  Port 3000 (Vercel/Node)  │             │   Port 8000 (Uvicorn)     │
   └─────────────┬─────────────┘             └─────────────┬─────────────┘
                 │                                         │
                 │ JSON API / Cookie Auth                  │ Async SQL (asyncpg)
                 └─────────────────────────────────────────┼──────────────────┐
                                                           │                  │
                                                           ▼                  ▼
                                              ┌──────────────────┐  ┌──────────────────┐
                                              │  PostgreSQL DB   │  │ External Gateway │
                                              │ (v15+ Persistent)│  │ (Stripe/Cashfree)│
                                              └──────────────────┘  └──────────────────┘
```

- **Frontend**: Next.js 15, React 19, TypeScript, Vanilla CSS design tokens, zero external UI component bloat.
- **Backend API**: Python 3.12+, FastAPI, Uvicorn, SQLAlchemy 2.0 Async, Pydantic v2.
- **Database**: PostgreSQL 15+ (`postgresql+asyncpg://`) with connection pooling and SSL mode.
- **Migrations**: Alembic async migrations (`alembic upgrade head`).
- **Security**: HttpOnly SameSite cookies, JWT with UUID `jti` invalidation, SHA-256 cryptographic audit ledger, sliding-window rate limiting.

---

## 2. Environment Variables

### Backend Configuration (`backend/.env`)

```ini
# Application Metadata & Runtime
APP_ENV=production
APP_NAME=RecoverAI
DEBUG=false
HOST=0.0.0.0
PORT=8000
APP_URL=https://app.recoverai.io
API_URL=https://api.recoverai.io

# Persistent PostgreSQL Connection
DATABASE_URL=postgresql+asyncpg://recoverai_user:<STRONG_DB_PASSWORD>@db.internal:5432/recoverai_prod
DB_ECHO=false
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600

# Security & Session Authentication
JWT_SECRET_KEY=<GENERATE_64_CHAR_HEX_SECRET>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
COOKIE_NAME=recoverai_session
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=.recoverai.io

# CORS Allowed Origins (Comma-separated)
CORS_ORIGINS=https://app.recoverai.io,https://recoverai.io

# Payment Gateway Keys (Server-side only)
STRIPE_API_KEY=
STRIPE_WEBHOOK_SECRET=
CASHFREE_APP_ID=
CASHFREE_SECRET_KEY=
CASHFREE_WEBHOOK_SECRET=
GATEWAY_WEBHOOK_SECRET=
```

### Frontend Configuration (`frontend/.env.production`)

```ini
NEXT_PUBLIC_API_URL=https://api.recoverai.io
NEXT_PUBLIC_APP_ENV=production
```

---

## 3. Database Setup & Migrations

### 1. Provision Persistent PostgreSQL
Create a PostgreSQL 15+ database instance with dedicated credentials:
```sql
CREATE DATABASE recoverai_prod;
CREATE USER recoverai_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE recoverai_prod TO recoverai_user;
```

### 2. Run Database Migrations
Always run Alembic migrations prior to traffic routing:
```bash
cd backend
.venv/bin/alembic upgrade head
```

### 3. Migration Verification
Confirm database state:
```bash
.venv/bin/alembic current
```

---

## 4. Backend Deployment (Docker & Container Services)

### Dockerfile (`backend/Dockerfile`)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='*'"]
```

---

## 5. Frontend Deployment (Node / Next.js)

### Build & Start Commands
```bash
cd frontend
npm ci
npm run build
npm run start -- -p 3000
```

---

## 6. Webhook Configuration & Replay Protection

Configure webhooks in merchant payment gateway consoles:
- **Webhook Target URL**: `https://api.recoverai.io/api/v1/integrations/webhooks/{provider_name}?org_id={ORGANIZATION_ID}`
- **Signing Secret**: Configure the identical HMAC secret in RecoverAI Settings -> Integrations.
- **Deduplication**: RecoverAI automatically computes a SHA-256 hash of every incoming webhook body and records `provider_event_id` in the `webhook_events` table to reject duplicate deliveries.

---

## 7. Health Checks & Observability

### Endpoints
- `GET /health/live`: Fast liveness probe (200 OK) for container orchestrators.
- `GET /health/ready`: Readiness probe verifying live database connectivity (200 OK when connected, 503 Service Unavailable when DB is down).
- `GET /health`: Comprehensive operational telemetry.

### Logging
All incoming requests and security events are logged as structured JSON without passwords, tokens, or plaintext card numbers.

---

## 8. Backup Strategy & Disaster Recovery

- **Automated Snapshots**: Daily point-in-time recovery (PITR) enabled on production PostgreSQL.
- **Logical Backups**: Scheduled daily `pg_dump`:
  ```bash
  pg_dump -h db.internal -U recoverai_user -Fc recoverai_prod > /backups/recoverai_$(date +%Y%m%d_%H%M%S).dump
  ```
- **Backup Retention**: 30-day rolling retention stored in geo-redundant object storage.

---

## 9. Rollback Plan

### Application Rollback
1. Re-deploy the previous Git release tag / container SHA.
2. If schema changes need reverting, downgrade Alembic revisions:
   ```bash
   alembic downgrade -1
   ```
3. Restart backend workers:
   ```bash
   systemctl restart recoverai-backend
   ```
