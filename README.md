# RecoverAI

### Autonomous AI Revenue Recovery Platform

RecoverAI is an AI-powered revenue recovery platform that helps businesses identify, prioritize, and recover failed payment revenue while keeping financial actions governed by deterministic business policies.

The platform combines AI-based failure diagnosis with policy-controlled recovery, human approval gates, verified settlement, bounded retries, and a cryptographically linked audit trail.

---

## Problem

Failed payments create significant revenue leakage for subscription and digital businesses.

A failed transaction may be caused by:

- Temporary gateway or network failures
- Customer action requirements
- Expired payment information
- Hard declines
- Repeated failures
- Other payment-related issues

Automatically retrying every failed payment is unsafe and inefficient.

RecoverAI addresses this by determining **which transactions should be recovered, how they should be recovered, and when recovery must stop.**

---

## Solution

RecoverAI follows a controlled recovery pipeline:

**Detect → Diagnose → Decide → Guard → Recover → Verify**

The AI analyzes the failure and recommends a recovery action.

A deterministic policy engine then evaluates that recommendation against business rules before any recovery action is executed.

High-value transactions require human approval.

A transaction is counted as recovered only after successful settlement verification.

---

## Key Features

### AI Failure Diagnosis

The AI diagnostician analyzes transaction failure information and produces:

- Failure category
- Confidence score
- Probable root cause
- Recommended recovery action

### Deterministic Recovery Policies

AI recommendations are evaluated against explicit business rules.

Policies include:

- Temporary-failure recovery
- Hard-decline suppression
- Maximum retry limits
- High-value approval gates
- Idempotent execution controls
- Human escalation

### Human Approval

Transactions above the configured **₹25,000 threshold** require human approval before recovery execution.

This ensures that AI recommendations do not independently authorize financial actions.

### Verified Recovery

Revenue is counted as recovered only after successful settlement verification.

An attempted retry does not count as recovered revenue.

### Bounded Recovery

Recovery attempts are limited by explicit stopping rules.

Transactions that reach the maximum retry limit are stopped and escalated rather than retried indefinitely.

### Audit Trail

Recovery decisions and actions are recorded in a SHA-256 chained audit trail.

This provides tamper-evident visibility into:

- AI decisions
- Policy decisions
- Recovery actions
- Human approvals
- Verification events

### Multi-Tenant Architecture

Organizations are isolated at the application and data-access layers.

Users can manage their own organization, transactions, recovery cases, integrations, and audit records.

---

## Demonstration

RecoverAI includes an isolated synthetic sandbox demonstrating the complete recovery workflow.

### Initial State

- Failed transactions: **50**
- Revenue at risk: **₹419,800**
- Verified recovered revenue: **₹0**
- Recovery rate: **0%**

### After Autonomous Recovery

- Transactions analyzed: **50**
- Automatically recovered: **24**
- Verified recovered revenue: **₹115,400**
- Recovery rate: **27.5%**
- In progress: **10**
- Awaiting human approval: **4**
- Hard declines blocked: **6**
- Transactions stopped/escalated: **6**

### After Human Approval

A high-value transaction of **₹50,000** is held because it exceeds the **₹25,000 human approval threshold**.

After approval and successful sandbox settlement verification:

- Verified recovered revenue: **₹165,400**
- Recovery rate: **39.4%**

All recovery figures are calculated from the application's persisted transaction data.

---

## Example Guardrails

### High-Value Transaction

**₹50,000 — Gateway Error**

- AI diagnosis: Temporary Failure
- AI confidence: 92%
- Recommended action: Delayed Retry
- Policy: High-Value Approval Gate
- Threshold: ₹25,000
- Result: Human approval required
- Final result: Verified sandbox recovery after approval

### Hard Decline

**₹12,000 — Card Stolen/Lost**

- AI diagnosis: Hard Decline
- AI confidence: 99%
- Policy: Hard-Decline Suppression
- Result: Recovery blocked
- Automated retries: 0

### Retry Limit

**₹4,200 — Repeated Failure**

- Previous attempts: 3
- Policy: Maximum Retry Limit
- Result: Recovery stopped and escalated
- No fourth automated retry

---

## Safety Model

RecoverAI follows a layered decision architecture:

**AI Diagnostician → Decision Engine → Deterministic Policy Engine → Human Approval Gate → Recovery Executor → Settlement Verification → Audit Trail**

The AI recommends actions.

The policy engine determines whether those actions are permitted.

The executor performs only policy-approved actions.

The verifier determines whether money was actually recovered.

The AI does **not** independently authorize financial actions.

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

## Technology Stack

### Frontend

- Next.js
- React
- TypeScript
- App Router

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

### Security

- JWT authentication
- Organization-level authorization
- Multi-tenant isolation
- HTTP-only cookie support
- CORS protection
- Rate limiting
- Secret redaction
- Webhook signature verification
- Idempotent execution controls
- SHA-256 audit chaining

---

## Application Flow

1. User creates an account.
2. User creates an organization/workspace.
3. Company information and recovery guardrails are configured.
4. Failed transactions are added through supported data sources.
5. RecoverAI detects failed transactions.
6. The AI diagnoses the probable failure reason.
7. The AI recommends a recovery action.
8. The deterministic policy engine evaluates the recommendation.
9. Unsafe or prohibited actions are blocked.
10. High-value actions are held for human approval.
11. Approved recovery actions are executed.
12. Settlement is independently verified.
13. Only verified settlements contribute to recovered revenue.
14. Every important decision and action is recorded in the audit trail.

---

## Project Structure

```text
recoverai/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── docs/
├── .env.example
└── .gitignore
```

---

## Local Development

### Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

The frontend requires the backend API URL through the appropriate environment variable.

---

## Environment Variables

Sensitive configuration is provided through environment variables.

Example configuration is provided in:

```text
.env.example
```

Production secrets must never be committed to the repository.

Typical configuration includes:

- Database connection
- JWT secret
- Application URL
- API URL
- CORS origins
- Payment provider configuration
- Runtime environment

---

## Testing

The application has been verified through automated and build checks.

Current verification:

- **37/37 backend tests passing**
- **0 TypeScript errors**
- **24/24 Next.js routes/build checks passing**
- Multi-tenant isolation verified
- Authentication and authorization verified
- Recovery workflow verified
- Policy guardrails verified
- Settlement verification verified
- SHA-256 audit chain verified
- Webhook idempotency verified

---

## Security

RecoverAI treats financial recovery as a controlled workflow rather than an unrestricted AI action.

Security and safety controls include:

- Tenant-isolated data access
- Authenticated API access
- Role-based authorization
- Password hashing
- JWT session security
- Rate limiting
- CORS restrictions
- Webhook signature verification
- Idempotency controls
- Hard-decline suppression
- Maximum retry limits
- Human approval for high-value transactions
- Verified settlement before revenue recognition
- Cryptographically linked audit records

---

## Deployment

The application is structured as separate frontend and backend services.

The production architecture consists of:

```text
User
 │
 ▼
Next.js Frontend
 │
 ▼
FastAPI Backend
 │
 ├── PostgreSQL
 │
 ├── Recovery Engine
 │
 ├── Policy Engine
 │
 ├── Authentication
 │
 └── Audit System
```

The deployed demonstration uses a sandbox/mock payment environment.

Live payment-provider credentials are required before using the system for real financial transactions.

---

## Demo Safety

The demonstration dataset is synthetic.

No real customer funds are moved during the demonstration.

The sandbox demonstrates:

- AI diagnosis
- Policy enforcement
- Human approval
- Recovery execution
- Settlement verification
- Retry stopping
- Hard-decline suppression
- Auditability
- Revenue reconciliation

The reported recovery metrics come from the application's persisted sandbox data.

---

## Why RecoverAI?

RecoverAI is designed around a simple principle:

> **AI should recommend. Policies should govern. Humans should control high-risk actions. Verification should determine success.**

Instead of blindly retrying failed payments, RecoverAI creates a controlled revenue recovery loop that balances:

- Recovery rate
- Financial safety
- Customer experience
- Operational efficiency
- Human oversight
- Auditability

---

## Project Status

RecoverAI has completed its end-to-end demonstration workflow, including:

- Authentication
- Organization onboarding
- Multi-tenant isolation
- Transaction ingestion
- AI diagnosis
- Recovery decisioning
- Deterministic policy enforcement
- Human approval
- Bounded retries
- Recovery execution
- Settlement verification
- Audit logging
- Sandbox demonstration
- Production deployment architecture

---

## License

© 2026 Bhumika Mistri. All rights reserved.
