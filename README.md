# RecoverAI

### Autonomous AI Revenue Recovery Platform

RecoverAI is a full-stack AI-powered revenue recovery platform that helps businesses identify failed payments, diagnose failure causes, determine safe recovery strategies, and execute policy-governed recovery workflows.

The platform combines AI-driven diagnosis with deterministic business policies, human approval controls, verified settlement, bounded retries, multi-tenant architecture, and a cryptographically linked audit trail.

---

## Problem

Failed payments can result from temporary gateway failures, customer action requirements, expired payment information, hard declines, or repeated failures.

Blindly retrying every failed transaction can create unnecessary customer friction and unsafe financial actions.

RecoverAI addresses this by determining:

- Why a payment failed
- Whether recovery should be attempted
- Which recovery action is appropriate
- Whether human approval is required
- When automated recovery should stop
- Whether the payment was actually recovered

---

## Solution

RecoverAI follows a controlled recovery workflow:

**Detect → Diagnose → Decide → Guard → Recover → Verify**

The AI analyzes transaction failures and recommends recovery actions.

A deterministic policy engine evaluates those recommendations against explicit business rules before execution.

High-value transactions can require human approval, while unsafe recovery attempts such as hard declines or exhausted retries are blocked or stopped.

Revenue is recognized as recovered only after successful settlement verification.

---

## Key Features

### AI Failure Diagnosis

Analyzes failed payment information and determines:

- Failure category
- Confidence score
- Probable root cause
- Recommended recovery action

### Deterministic Policy Engine

AI recommendations are evaluated against explicit business rules.

Policies include:

- Temporary-failure recovery
- Hard-decline suppression
- Maximum retry limits
- High-value approval gates
- Idempotent execution controls
- Human escalation

### Human Approval

High-value transactions above the configured business threshold require human approval before recovery execution.

This prevents the AI from independently authorizing high-risk financial actions.

### Verified Recovery

A transaction is counted as recovered only after successful settlement verification.

An attempted retry does not count as recovered revenue.

### Bounded Recovery

Recovery attempts are limited by predefined stopping rules.

Transactions that reach the maximum retry limit are stopped and escalated instead of being retried indefinitely.

### Multi-Tenant Architecture

Organizations are isolated at the application and data-access layers.

Each organization manages its own:

- Transactions
- Recovery cases
- Users
- Settings
- Integrations
- Audit records

### Audit Trail

Important recovery events are recorded using a SHA-256 chained audit trail.

The audit trail captures:

- AI decisions
- Policy decisions
- Recovery actions
- Human approvals
- Verification events
- Authentication events
- System events

### Provider-Agnostic Integration

RecoverAI uses an abstraction layer for payment providers, allowing the recovery engine to work independently of a specific payment gateway.

The architecture supports sandbox/mock processing and provider adapters.

---

## Safety Model

RecoverAI separates AI reasoning from financial authorization.

**AI recommends. Policies govern. Humans approve high-risk actions. Verification confirms recovery.**

The decision flow is:

**AI Diagnostician → Decision Engine → Deterministic Policy Engine → Human Approval Gate → Recovery Executor → Settlement Verifier → Audit Trail**

The AI does not independently authorize financial actions.

---

## Architecture

```text
                    ┌─────────────────────┐
                    │     Transactions    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   AI Diagnostician  │
                    │  Failure + Cause    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Decision Engine   │
                    │ Recovery Recommendation│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Deterministic      │
                    │    Policy Engine    │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │ Human Approval   │      │ Policy Approved  │
        │ Required         │      │ Recovery         │
        └────────┬─────────┘      └────────┬─────────┘
                 │                         │
                 └────────────┬────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Recovery Executor   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Settlement Verifier │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ SHA-256 Audit Trail │
                    └─────────────────────┘
```

---

## Application Flow

1. User creates an account.
2. User creates an organization/workspace.
3. Company information and recovery guardrails are configured.
4. Transactions are added through supported data sources.
5. RecoverAI detects failed transactions.
6. The AI diagnoses the probable failure reason.
7. The AI recommends a recovery action.
8. The deterministic policy engine evaluates the recommendation.
9. Unsafe or prohibited actions are blocked.
10. High-value actions are held for human approval.
11. Approved recovery actions are executed.
12. Settlement is independently verified.
13. Only verified settlements contribute to recovered revenue.
14. Recovery decisions and actions are recorded in the audit trail.

---

## Technology Stack

### Frontend

- Next.js
- React
- TypeScript
- Next.js App Router

### Backend

- FastAPI
- Python
- SQLAlchemy
- Alembic
- JWT authentication
- bcrypt password hashing

### Database

- PostgreSQL
- SQLite development support

### APIs and Integration

- REST APIs
- Provider abstraction layer
- Webhook processing
- Webhook signature verification
- Idempotent event handling

### Security

- JWT authentication
- Organization-level authorization
- Multi-tenant isolation
- Secure cookies
- CORS protection
- Rate limiting
- Secret redaction
- Webhook signature verification
- Idempotent execution controls
- SHA-256 audit chaining

---

## Project Structure

```text
recoverai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── package-lock.json
│
├── docs/
├── .env.example
└── .gitignore
```

---

# Installation & Setup

## Prerequisites

Install the following before running RecoverAI locally:

- Python 3.12+
- Node.js 20+
- npm
- PostgreSQL 15+ or SQLite
- Git

Clone the repository:

```bash
git clone https://github.com/Bhumika168/recoverai.git
cd recoverai
```

---

## Backend Setup

Move into the backend directory:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment.

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

---

## Backend Environment Configuration

Create a backend `.env` file using the example configuration:

```bash
cp .env.example .env
```

Configure the required environment variables.

Example:

```env
ENVIRONMENT=development
DEBUG=true

DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/recoverai

JWT_SECRET_KEY=your-secret-key

JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

COOKIE_SECURE=false
COOKIE_SAMESITE=lax
COOKIE_NAME=recoverai_session

PAYMENT_PROVIDER=mock

LOG_LEVEL=INFO
```

For local SQLite development, configure the database URL according to the application's supported SQLite configuration.

Never commit real secrets or production credentials to GitHub.

---

## Database Setup

Make sure PostgreSQL is running if you are using PostgreSQL.

Create the RecoverAI database:

```sql
CREATE DATABASE recoverai;
```

From the `backend` directory, run the database migrations:

```bash
alembic upgrade head
```

This creates the required database schema.

---

## Start the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://localhost:8000
```

API endpoints are available under:

```text
http://localhost:8000/api/v1
```

---

## Frontend Setup

Open a new terminal and move to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create the frontend environment file:

```bash
cp .env.example .env.local
```

Configure the backend API URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the development server:

```bash
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

---

## Running the Application

Start both services.

### Terminal 1 — Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:3000
```

Create an account, create an organization, configure the workspace, and begin using the recovery workflow.

---

## Production Build

### Frontend

From the `frontend` directory:

```bash
npm install
npm run build
npm start
```

### Backend

From the `backend` directory:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Environment Variables

RecoverAI uses environment variables for runtime configuration and secrets.

Important configuration includes:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `APP_URL`
- `API_URL`
- `CORS_ORIGINS`
- `COOKIE_SECURE`
- `COOKIE_SAMESITE`
- `PAYMENT_PROVIDER`
- `NEXT_PUBLIC_API_URL`

Refer to `.env.example` for the available configuration structure.

Production secrets must never be committed to the repository.

---

## Testing

RecoverAI includes automated backend tests and frontend build/type validation.

Run backend tests:

```bash
cd backend
pytest
```

Run frontend checks:

```bash
cd frontend
npm run build
```

The application has been validated for:

- Authentication
- Authorization
- Multi-tenant isolation
- Organization management
- Transaction management
- Recovery workflows
- Policy enforcement
- Human approval
- Retry stopping
- Settlement verification
- Webhook handling
- Idempotent execution
- Audit logging
- Security controls

---

## Security

RecoverAI treats revenue recovery as a controlled financial workflow.

Security controls include:

- Tenant-isolated data access
- Authenticated API access
- Organization-level authorization
- Password hashing
- JWT-based authentication
- Secure session handling
- Rate limiting
- CORS restrictions
- Webhook signature verification
- Idempotent execution
- Hard-decline suppression
- Maximum retry limits
- Human approval for high-value transactions
- Verified settlement before revenue recognition
- Cryptographically linked audit records
- Secret redaction

---

## Deployment

RecoverAI can be deployed as separate frontend and backend services.

The production architecture consists of:

```text
                    ┌───────────────────┐
                    │       User        │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Next.js Frontend  │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  FastAPI Backend  │
                    └─────────┬─────────┘
                              │
                 ┌────────────┼────────────┐
                 │            │            │
                 ▼            ▼            ▼
           PostgreSQL    Recovery Engine  Audit System
```

The deployed application uses a sandbox/mock payment environment for safe demonstration and development.

Live payment credentials should only be configured when real financial processing is intentionally enabled.

---

## Demo Safety

RecoverAI provides a synthetic sandbox environment for testing and demonstration.

The sandbox is designed to demonstrate:

- AI diagnosis
- Recovery decisioning
- Deterministic policy enforcement
- Human approval
- Recovery execution
- Settlement verification
- Hard-decline suppression
- Retry stopping
- Auditability
- Revenue reconciliation

No real customer funds are moved during sandbox operation.

---

## Design Principles

RecoverAI is built around four principles:

### AI Should Recommend

AI is responsible for analyzing failures and recommending appropriate recovery actions.

### Policies Should Govern

Deterministic business rules decide whether an AI recommendation is permitted.

### Humans Should Control High-Risk Actions

High-value or sensitive recovery actions can require explicit human approval.

### Verification Should Determine Success

A recovery attempt is not considered successful until settlement is verified.

---

## Project Status

RecoverAI includes an end-to-end implementation of:

- User authentication
- Organization onboarding
- Multi-tenant isolation
- Transaction ingestion
- AI failure diagnosis
- Recovery decisioning
- Deterministic policy enforcement
- Human approval workflows
- Bounded retries
- Recovery execution
- Settlement verification
- Payment provider abstraction
- Webhook processing
- Idempotency controls
- SHA-256 audit logging
- Sandbox recovery workflows
- Production deployment architecture

---

## Live Application

**RecoverAI:**  
https://recoverai-frontend-3ny5.onrender.com

**GitHub Repository:**  
https://github.com/Bhumika168/recoverai

---

## License

© 2026 Bhumika Mistri. All rights reserved.
