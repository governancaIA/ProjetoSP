# Software Design Document — FiscalAI

| Field | Value |
|---|---|
| **Version** | 1.0.0 |
| **Date** | 2026-05-27 |
| **Status** | Draft — MVP |
| **Authors** | Jianv (product), Paige/BMad (documentation) |
| **Classification** | Internal — Engineering |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Architecture](#3-architecture)
4. [Component Design](#4-component-design)
5. [Data Design](#5-data-design)
6. [Interface Design](#6-interface-design)
7. [Fiscal Rule Engine](#7-fiscal-rule-engine)
8. [Security Design](#8-security-design)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Deployment](#10-deployment)
11. [Epic & Feature Status](#11-epic--feature-status)

---

## 1. Introduction

### 1.1 Purpose

This document describes the software architecture, component design, data models, and interface contracts of **FiscalAI** — a B2B SaaS platform for automated Brazilian fiscal document auditing. It serves as the authoritative technical reference for engineers, AI coding agents, and reviewers working on the system.

### 1.2 Problem Statement

Brazilian companies face systematic fiscal compliance risk:

- NF-e values in SPED diverge from the original XML (transcription errors)
- Cancelled invoices remain booked in EFD fiscal records
- Outgoing NF-e documents lack corresponding SPED bookings
- Cancelled CT-e transport documents are incorrectly kept in SPED
- Tax values (ICMS, PIS, COFINS, IPI) differ between SPED and XML
- 100% manual auditing is expensive, slow, and error-prone
- Fines (multas) for avoidable inconsistencies are disproportionately high

### 1.3 Value Proposition

FiscalAI **automatically detects fiscal inconsistencies before they become fines** — replacing days of manual analyst work with minutes of automated validation, reducing operational risk, cost, and dependency on scarce tax expertise.

### 1.4 Target Market

Brazilian companies obligated to file:
- SPED Fiscal (EFD ICMS/IPI)
- EFD Contribuições (PIS/COFINS)
- NF-e (Nota Fiscal Eletrônica)
- CT-e (Conhecimento de Transporte Eletrônico)

### 1.5 Scope of This Document

This SDD covers the MVP architecture (30-day horizon) and annotates planned extensions for the Beta (90 days) and Scale (180 days) phases. It does not cover the AI/ML anomaly detection layer (Epic 3, Phase 2) or ERP integrations (Epic 9, Phase 3).

---

## 2. System Overview

### 2.1 High-Level Context (C4 Level 1)

```
┌──────────────────────────────────────────────────────────────┐
│                        FiscalAI                              │
│                                                              │
│  ┌─────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │Frontend │◄──►│  Backend API │◄──►│  Worker (Celery)   │  │
│  │(React)  │    │  (FastAPI)   │    │  Parse + Validate  │  │
│  └─────────┘    └──────┬───────┘    └─────────┬──────────┘  │
│                        │                      │             │
│               ┌────────┼──────────────────────┤             │
│               ▼        ▼                      ▼             │
│          ┌─────────┐ ┌──────┐          ┌──────────────┐     │
│          │ MinIO   │ │Redis │          │ PostgreSQL   │     │
│          │(Files)  │ │Queue │          │(Multi-tenant)│     │
│          └─────────┘ └──────┘          └──────────────┘     │
└──────────────────────────────────────────────────────────────┘
         │                                           │
         ▼                                           ▼
   [Tax Analysts]                           [Anthropic API]
   (Web Browser)                          (Report Narratives)
```

### 2.2 Core User Flow

```
1. Analyst uploads SPED .txt or XML NF-e/CT-e files
2. API streams file to MinIO, queues a Celery parse task
3. Worker detects format → parses → normalizes → stores in PostgreSQL
4. Worker triggers validation: DAG of fiscal rules executes
5. Scoring service aggregates results → risk score 0–100
6. Dashboard shows inconsistencies, priority queue, risk trend
7. Analyst exports PDF/Excel report (optionally with AI narrative)
```

---

## 3. Architecture

### 3.1 Architecture Style

**Event-driven, three-tier, multi-tenant SaaS** with schema-per-tenant isolation.

- **Tier 1:** React SPA (browser)
- **Tier 2:** FastAPI stateless API + Celery async workers
- **Tier 3:** PostgreSQL (multi-tenant), Redis (queue + cache), MinIO (object storage)

### 3.2 Infrastructure Diagram

```
VPS Hostinger (Docker Compose — MVP)
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌────────────────┐    ┌────────────────┐                   │
│  │  nginx         │    │  FastAPI       │                   │
│  │  :80 / :443    │───►│  :8000         │                   │
│  │  (reverse      │    │  (uvicorn)     │                   │
│  │   proxy)       │    └───────┬────────┘                   │
│  └────────────────┘            │                           │
│                                │ enqueue                    │
│  ┌─────────────────┐           ▼                           │
│  │  React/Nginx    │    ┌──────────────┐                   │
│  │  :5173 (dev)    │    │  Redis       │                   │
│  │  :80 (prod)     │    │  :6379       │◄──────────────┐   │
│  └─────────────────┘    └──────────────┘               │   │
│                                │ consume                │   │
│                                ▼                        │   │
│                         ┌──────────────────────────┐   │   │
│                         │  Celery Workers (4x)     │   │   │
│                         │  parse_document          │   │   │
│                         │  validate_document       ├───┘   │
│                         └──────────┬───────────────┘       │
│                                    │                        │
│               ┌────────────────────┼──────────────┐        │
│               ▼                    ▼               ▼        │
│  ┌────────────────────┐  ┌──────────────┐  ┌──────────┐   │
│  │  PostgreSQL :5432  │  │  MinIO :9000 │  │  Flower  │   │
│  │  (multi-tenant     │  │  (files)     │  │  :5555   │   │
│  │   schema-per-org)  │  └──────────────┘  └──────────┘   │
│  └────────────────────┘                                     │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Multi-tenancy | Schema-per-tenant in PostgreSQL | Maximum isolation; LGPD-auditable; zero cost on shared DB |
| Object storage | MinIO (local S3-compatible) | $0 cost on existing VPS; `boto3` abstraction enables zero-code migration to AWS S3 |
| Task queue | Celery + Redis | Handles 50–100 clients at ~100 jobs/min on VPS; Flower monitoring built-in |
| Rule execution | DAG (topological order) | Rules have dependencies; Kahn's algorithm ensures correct order without cycles |
| API framework | FastAPI | Async I/O; automatic OpenAPI docs; Pydantic v2 validation at boundaries |
| Frontend state | TanStack Query v5 | Server-state caching; no Redux complexity needed at MVP scale |
| File streaming | Temp file + MinIO put_object | Caps RAM at 8 MB/upload regardless of file size (vs. 2 GB in-memory) |

---

## 4. Component Design

### 4.1 Backend Components

```
backend/app/
├── main.py              ← FastAPI app, middleware chain, lifespan
├── core/
│   ├── config.py        ← Pydantic Settings (env vars, validation)
│   ├── database.py      ← Engine, SessionLocal, tenant schema routing
│   ├── security.py      ← JWT encode/decode, password hashing
│   ├── middleware.py     ← TenantMiddleware (sets search_path per request)
│   ├── celery_app.py    ← Celery app instance
│   └── logging_config.py← Structured JSON logging (python-json-logger)
│
├── models/              ← SQLAlchemy ORM (declarative, 2.0 style)
│   ├── user.py          ← User, Organization, RefreshToken
│   ├── document.py      ← Document (raw upload record)
│   ├── fiscal_document.py← FiscalDocument, FiscalItem (normalized)
│   ├── ct_document.py   ← CtDocument (CT-e normalized)
│   └── rule_log.py      ← RuleExecutionLog, SeverityLevel enum
│
├── schemas/             ← Pydantic v2 request/response contracts
│   ├── auth.py
│   └── documents.py
│
├── parsers/             ← File format detection and parsing
│   ├── detector.py      ← Auto-detect: SPED EFD, NF-e XML, CT-e XML
│   ├── sped_efd_icms.py ← SPED EFD ICMS/IPI (blocks 0,C,D,E,G,H,K)
│   ├── nfe_xml.py       ← NF-e XML v4.0
│   └── cte_xml.py       ← CT-e XML v3.0
│
├── validators/          ← Fiscal rule engine
│   └── rules/
│       ├── base.py      ← BaseRule ABC, RuleResult dataclass
│       ├── dag.py       ← RuleDAG (Kahn's topological sort)
│       ├── registry.py  ← Rule registry (maps rule_id → instance)
│       └── fiscal_rules.py ← All 8 MVP rule implementations
│
├── services/            ← Business logic
│   ├── auth_service.py
│   ├── document_service.py
│   ├── rule_service.py  ← Orchestrates DAG execution per tenant config
│   ├── scoring_service.py← Risk scoring (0–100), penalty estimation
│   ├── report_service.py ← PDF (ReportLab), Excel (openpyxl), AI narrative
│   └── storage_service.py← MinIO upload_stream/upload/download/delete
│
├── api/                 ← FastAPI routers (all under /api/v1/)
│   ├── deps.py          ← get_db, get_current_user dependencies
│   ├── auth.py          ← /login, /refresh, /register, /logout
│   ├── uploads.py       ← POST /uploads (streaming, multi-file)
│   ├── documents.py     ← GET /documents, GET /documents/{id}
│   ├── validation.py    ← POST /validate, GET /validation-results
│   ├── jobs.py          ← GET /jobs/{id} (Celery task status polling)
│   └── reports.py       ← POST /reports (PDF/Excel generation)
│
└── tasks/               ← Celery async tasks
    ├── parse_document.py   ← detect → parse → store → trigger validate
    └── validate_document.py← rule DAG execution + scoring
```

### 4.2 Frontend Components

```
frontend/src/
├── App.tsx              ← Router setup, auth guard
├── pages/               ← Route-level components (one per URL)
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── DocumentsPage.tsx
│   ├── DocumentDetailPage.tsx
│   ├── ReportsPage.tsx
│   └── SettingsPage.tsx
│
├── components/
│   ├── ui/              ← shadcn/ui primitives (Button, Input, etc.)
│   ├── layout/          ← Sidebar, Header, Layout wrapper
│   ├── dashboard/       ← RiskScoreCard, AlertSummary, TrendChart
│   ├── documents/       ← UploadZone (drag-drop), DocumentList, StatusBadge
│   └── document-detail/ ← InconsistencyTable, RuleResultRow
│
├── hooks/               ← Custom React hooks (TanStack Query wrappers)
│   ├── useJobPolling.ts  ← Polls /jobs/{id} until done
│   ├── useDocuments.ts
│   ├── useDocumentScore.ts
│   ├── usePeriodScore.ts
│   ├── useAlertQueue.ts
│   └── useValidationResults.ts
│
├── contexts/
│   └── AuthContext.tsx   ← JWT storage, user state, logout
│
├── services/
│   └── api.ts           ← Axios instance + interceptors (auth header injection)
│
├── types/               ← TypeScript interfaces
│   ├── api.ts           ← API response shapes
│   └── auth.ts          ← User, AuthState
│
└── lib/
    └── utils.ts         ← cn() (Tailwind class merge), formatBRL(), formatDate()
```

### 4.3 Celery Task Chain

```
POST /uploads
    │
    ▼
[API] stream → MinIO → create Document record → enqueue
    │
    ▼
[parse_document task]
    detect_format()
    ├── SPED: sped_efd_icms.parse() → FiscalDocument + FiscalItem records
    ├── NF-e XML: nfe_xml.parse()   → FiscalDocument + FiscalItem records
    └── CT-e XML: cte_xml.parse()   → CtDocument record
    update Document.status = "parsed"
    │
    ▼
[validate_document task]
    rule_service.execute_all(document, tenant_config)
        └── RuleDAG.execute() → [RuleResult, ...]
    scoring_service.score_document(rule_results)
    store RuleExecutionLog records
    update Document.status = "validated"
    │
    ▼
[Frontend] useJobPolling() detects "validated" → refreshes dashboard
```

---

## 5. Data Design

### 5.1 Multi-Tenancy Schema Pattern

```sql
-- Shared across all tenants (public schema)
public.organizations  → tenant metadata, plan, billing
public.users          → auth; org_id FK
public.refresh_tokens → JWT refresh token revocation list
public.cfop_reference → ~2000 valid CFOP codes (Brazilian fiscal reference)
public.cst_icms_reference → CST codes per tax regime
public.tipi_ncm       → NCM ↔ IPI rate table (planned: EPIC 12)

-- Per-tenant (isolated — schema: tenant_{org_id})
tenant_<id>.documents         → raw upload records
tenant_<id>.fiscal_documents  → normalized NF-e/SPED documents
tenant_<id>.fiscal_items      → line items (C170)
tenant_<id>.ct_documents      → normalized CT-e documents
tenant_<id>.rule_logs         → one row per rule per document execution
tenant_<id>.tenant_config     → per-tenant rule tolerance overrides
```

### 5.2 Core Data Models

#### Document (upload record)
```
documents
├── id              INTEGER PK
├── tenant_id       VARCHAR(100)     FK → organization
├── file_name       VARCHAR(255)
├── file_hash       VARCHAR(64)      SHA-256; used for dedup
├── storage_key     VARCHAR(500)     MinIO path: {tenant_id}/{type}/{hash}.ext
├── document_type   ENUM             sped_efd_icms | nfe | cte | efd_contribuicoes
├── status          ENUM             uploaded | parsing | parsed | validating | validated | error
├── file_size       BIGINT           bytes
├── celery_task_id  VARCHAR(255)     for polling
└── created_at      TIMESTAMP
```

#### FiscalDocument (normalized NF-e / SPED C100)
```
fiscal_documents
├── id                      INTEGER PK
├── tenant_id               VARCHAR(100)
├── document_id             INTEGER FK → documents
├── chave_acesso            VARCHAR(44)   44-digit NF-e access key (unique index)
├── numero_nf               VARCHAR(20)
├── serie                   VARCHAR(20)
├── emitente_cnpj           VARCHAR(14)   index
├── emitente_nome           VARCHAR(255)
├── destinatario_cnpj       VARCHAR(14)
├── data_emissao            DATE          index
├── natureza                VARCHAR(50)   saída | entrada | devolução | complementar
├── valor_total             NUMERIC(15,2)
├── valor_icms              NUMERIC(15,2)
├── valor_pis               NUMERIC(15,2)
├── valor_cofins            NUMERIC(15,2)
├── valor_ipi               NUMERIC(15,2)
├── status_nfe              VARCHAR(50)   autorizado | cancelado | denegado
├── protocolo_nfe           VARCHAR(50)
├── data_autorizacao        TIMESTAMP
├── chave_acesso_referenciada VARCHAR(44) (for devolução/complementar)
├── document_version        INTEGER       for reprocessing (superseded flag)
├── superseded              BOOLEAN
└── created_at / updated_at TIMESTAMP
```

#### FiscalItem (SPED C170 / NF-e items)
```
fiscal_items
├── id                    INTEGER PK
├── tenant_id             VARCHAR(100)
├── fiscal_document_id    INTEGER FK
├── item_seq              INTEGER
├── codigo_produto        VARCHAR(60)
├── ncm                   VARCHAR(8)      8-digit NCM code
├── cfop                  VARCHAR(4)      4-digit CFOP
├── cst                   VARCHAR(3)      2 or 3-digit CST
├── quantidade            NUMERIC(15,4)
├── valor_unitario        NUMERIC(15,2)
├── valor_item            NUMERIC(15,2)
├── base_icms / aliquota_icms / valor_icms
├── base_pis  / aliquota_pis  / valor_pis
├── base_cofins / aliquota_cofins / valor_cofins
└── valor_ipi             NUMERIC(15,2)
```

#### RuleExecutionLog
```
rule_logs
├── id                INTEGER PK
├── fiscal_document_id INTEGER FK
├── tenant_id         VARCHAR(100)
├── rule_id           VARCHAR(50)    e.g. "NF_VALOR_DIVERGENTE"
├── rule_version      VARCHAR(20)    semantic version "1.0.0"
├── passed            BOOLEAN
├── severity          ENUM           CRITICAL | HIGH | MEDIUM | LOW | INFO
├── message           TEXT
├── input_snapshot    JSONB          values used in comparison (audit trail)
├── config_applied    JSONB          tenant-specific config (tolerance, etc.)
└── executed_at       TIMESTAMP
```

### 5.3 Storage Key Convention

```
MinIO bucket: fiscalai-documents

Key pattern:  {tenant_id}/{document_type}/{sha256_hex}.{ext}

Examples:
  org_001/sped_efd_icms/a3f9bc7d...4e21.txt
  org_001/nfe/b7e2c1a0...9f44.xml
  org_002/cte/c8d3e5b1...7a22.xml
```

Deduplication: `file_hash` (SHA-256) is unique-indexed per tenant. Duplicate uploads are rejected before MinIO write.

---

## 6. Interface Design

### 6.1 API Conventions

- Base URL: `/api/v1/`
- Authentication: `Authorization: Bearer <access_token>` on all protected routes
- All responses: `application/json`
- Error format: `{"detail": "human-readable message"}`

### 6.2 Core Endpoints

#### Authentication
```
POST /api/v1/auth/register      → 201 { user_id, email, org_id }
POST /api/v1/auth/login         → 200 { access_token, refresh_token, expires_in }
POST /api/v1/auth/refresh       → 200 { access_token, expires_in }
POST /api/v1/auth/logout        → 204 (revokes refresh token)
```

#### Uploads
```
POST /api/v1/uploads
  Body: multipart/form-data; files[]=...
  → 201 { jobs: [{ job_id, file_name, status }] }

# Rate limit: 10 uploads/minute per IP
# Max file size: 2 GB per file
# Accepted types: text/plain (SPED), application/xml, text/xml (NF-e, CT-e)
```

#### Jobs (async polling)
```
GET /api/v1/jobs/{job_id}
  → 200 { job_id, status, progress, result, error }
  # status: queued | parsing | parsed | validating | validated | error
```

#### Documents
```
GET /api/v1/documents                → paginated list
GET /api/v1/documents/{id}           → full document with items
GET /api/v1/documents/{id}/results   → validation results (rule logs)
GET /api/v1/documents/{id}/score     → risk score + severity breakdown
```

#### Validation
```
POST /api/v1/validate/{document_id}  → 202 { job_id }  (triggers revalidation)
GET  /api/v1/validation-results      → filtered list of rule failures
```

#### Dashboard / Scoring
```
GET /api/v1/periods/{year}/{month}/score    → { score, severity_counts, delta }
GET /api/v1/alerts/priority-queue          → sorted list by (severity × exposure)
```

#### Reports
```
POST /api/v1/reports
  Body: { document_ids[], format: "pdf"|"excel", include_ai_narrative: bool }
  → 202 { job_id }

GET /api/v1/reports/{job_id}/download → binary stream (PDF or XLSX)
```

### 6.3 Frontend ↔ Backend Contract

```typescript
// Job polling (useJobPolling.ts)
interface JobStatus {
  job_id: string
  status: 'queued' | 'parsing' | 'parsed' | 'validating' | 'validated' | 'error'
  progress: number        // 0–100
  result?: DocumentResult
  error?: string
}

// Risk score
interface PeriodScore {
  year: number
  month: number
  score: number           // 0–100 (100 = critical risk)
  severity_counts: {
    critical: number
    high: number
    medium: number
    low: number
  }
  delta: number           // vs previous period
  estimated_exposure_brl: number
}

// Rule execution result
interface ValidationResult {
  rule_id: string
  rule_version: string
  passed: boolean
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  message: string
}
```

### 6.4 Axios Configuration

All API calls go through the configured instance in `src/services/api.ts`. The interceptor:
1. Injects `Authorization: Bearer <token>` on every request
2. On 401 response → attempts silent token refresh
3. On refresh failure → redirects to `/login`

---

## 7. Fiscal Rule Engine

### 7.1 Architecture

```
RuleRegistry  →  RuleDAG  →  BaseRule.execute()  →  RuleResult
                  (Kahn)       (per rule)           (pass/fail)
                    │
                    ▼
             RuleService.execute_all()
                    │
                    ▼
             ScoringService.score()
                    │
                    ▼
             RuleExecutionLog (persisted)
```

### 7.2 Implemented Rules (MVP)

| Rule ID | Description | Severity | Status |
|---|---|---|---|
| `NF_VALOR_DIVERGENTE` | NF-e total value in SPED ≠ XML value | HIGH | ✅ Done |
| `NF_CANCELADA_NO_SPED` | Cancelled NF-e (event 110111) still booked in SPED | CRITICAL | ✅ Done |
| `NF_SAIDA_SEM_LANCAMENTO` | NF-e saída without C100 in EFD | HIGH | ✅ Done (partial) |
| `CTE_CANCELADO_NO_SPED` | Cancelled CT-e still in D100 | CRITICAL | ✅ Done |
| `ICMS_DIVERGENTE` | ICMS calculated ≠ declared (tolerance R$0.50/item) | HIGH | ✅ Done |
| `CST_INCOMPATIVEL_PIS_COFINS` | PIS/COFINS CST incompatible with tax regime | MEDIUM | ✅ Done |
| `CFOP_INVALIDO` | CFOP invalid for operation type/UF | HIGH | ✅ Done |
| `IPI_ALIQUOTA_TIPI` | IPI rate diverges from TIPI for declared NCM | MEDIUM | ❌ Pending (Epic 12) |

### 7.3 Adding a New Rule

```python
# 1. Subclass BaseRule in fiscal_rules.py
class MyNewRule(BaseRule):
    rule_id = "MY_NEW_RULE"
    rule_version = "1.0.0"
    depends_on = []  # list rule_ids that must run first

    def execute(self, fiscal_document, items: list, config: dict) -> RuleResult:
        # config contains tenant-specific overrides
        tolerance = config.get("tolerance_brl", Decimal("0.01"))
        if condition:
            return self._pass("Rule passed", input_snapshot={...})
        return self._fail(
            SeverityLevel.HIGH,
            f"Inconsistency: {detail}",
            input_snapshot={"sped_val": ..., "xml_val": ...},
            config_applied={"tolerance_brl": str(tolerance)},
        )

# 2. Register in registry.py
# 3. Write tests (required): passing path, failing path, edge cases
```

### 7.4 Tenant Configuration

Rules can be tuned per tenant via `tenant_config` table:

```json
{
  "tolerance_brl": "0.05",
  "disabled_rules": ["NF_SAIDA_SEM_LANCAMENTO"],
  "icms_tolerance_per_item": "0.50"
}
```

Default values are hard-coded in each rule; DB overrides take precedence.

### 7.5 Risk Scoring

```
score = weighted_sum(rule_results) / max_possible_score × 100

Weights:
  CRITICAL → 40 points
  HIGH     → 20 points
  MEDIUM   →  8 points
  LOW      →  2 points
  INFO     →  0 points

Score bands:
  0–30   → GREEN  (low risk)
  31–60  → YELLOW (moderate risk)
  61–80  → ORANGE (high risk)
  81–100 → RED    (critical — regulatory action likely)

Financial exposure: estimated via art. 12 DL 1598 + Portaria CAT penalty tables
```

---

## 8. Security Design

### 8.1 Authentication

```
[Client]  POST /auth/login  →  [API]  →  DB (verify bcrypt hash)
                                    ↓
                           access_token (HS256 JWT, 30 min)
                           refresh_token (opaque, 7 days, DB-stored)
```

- Access tokens: short-lived (30 min), stateless JWT
- Refresh tokens: stored in DB with revocation support; logout invalidates token
- `SECRET_KEY` minimum 32 chars; default key raises `RuntimeError` in production

### 8.2 Multi-Tenant Isolation

Every request with a valid JWT extracts `tenant_id` → `TenantMiddleware` sets `search_path = tenant_<id>, public` before the route handler executes.

```python
# This runs before EVERY authenticated request
SET search_path TO "tenant_org_001", public
```

No route handler can accidentally read another tenant's data unless it explicitly bypasses `search_path` — which no application code does.

### 8.3 SQL Injection Prevention

PostgreSQL parameterized queries handle all data values. The only exception is schema name interpolation (PostgreSQL limitation — identifiers cannot be parameterized):

```python
# ALWAYS validated with regex before interpolation
_TENANT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{3,100}$")
# Raises ValueError if tenant_id contains unsafe characters
_validate_tenant_id(tenant_id)
schema_name = f"tenant_{tenant_id}"
session.execute(text(f'SET search_path TO "{schema_name}", public'))
```

### 8.4 LGPD Compliance

| Requirement | Implementation |
|---|---|
| No fiscal data in plain logs | CNPJ masked to first 4 digits; monetary values never logged |
| Data isolation | Schema-per-tenant; no cross-tenant queries possible |
| Audit trail | Every rule execution logged with `input_snapshot` (what was compared) |
| Data deletion | Tenant schema drop removes all PII; MinIO prefix delete removes all files |
| Access control | JWT-gated; RBAC planned (admin/analyst/viewer) |

### 8.5 Transport Security

- HTTPS enforced in production (nginx TLS termination)
- `MINIO_USE_SSL=True` in production
- CORS: explicit domain whitelist; never `*` with credentials
- Rate limiting: 10 requests/minute on upload; 100 requests/minute default

---

## 9. Non-Functional Requirements

### 9.1 Performance

| Metric | Target | Notes |
|---|---|---|
| Upload throughput | 2 GB file in <60 sec | Streaming; never load in RAM |
| Parse latency | <30 sec for typical SPED (50MB) | Celery worker, background |
| API response (read) | <200 ms p95 | Indexed queries, TanStack cache |
| Validation (7 rules) | <10 sec per document | In-memory DAG execution |
| Dashboard load | <1 sec | Aggregated scores pre-computed |

### 9.2 Scalability

```
MVP (1–5 clients):    1 VPS, 4 Celery workers, 1 PostgreSQL instance
Beta (10–30 clients): 8 Celery workers, MinIO backup to Wasabi (~$20/mo)
Phase 2 (50–100):     MinIO → AWS S3 (zero code change via boto3)
                      Celery broker → AWS SQS (URL swap)
Enterprise (100+):    Database-per-tenant (dedicated RDS for large orgs)
```

### 9.3 Reliability

- RPO (Recovery Point Objective): 24 hours (daily `pg_dump` to Wasabi)
- RTO (Recovery Time Objective): 4 hours (VPS restore from snapshot)
- MinIO: real-time replication to Wasabi for file durability
- Redis: ephemeral (queue state is recoverable — Celery retries)

### 9.4 Observability

| Layer | Tool |
|---|---|
| Structured logs | python-json-logger → JSON per line |
| Task monitoring | Flower (Celery Web UI at :5555) |
| Health check | `GET /health` → PostgreSQL + Redis + MinIO connectivity |
| Metrics (planned) | OpenTelemetry + Prometheus + Grafana |

Critical alerts:
- PostgreSQL connections > 90% of `max_connections`
- Redis memory > 90%
- MinIO disk < 10% free
- Celery queue depth > 100 tasks

---

## 10. Deployment

### 10.1 Development

```powershell
# Backend
cd backend
python -m venv venv; venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload   # :8000

# Frontend
cd frontend
npm install
npm run dev                               # :5173
```

### 10.2 Full Stack (Docker Compose)

```powershell
cd infra
docker-compose up -d
# API:      http://localhost:8000
# Frontend: http://localhost:5173
# Flower:   http://localhost:5555
# MinIO:    http://localhost:9000
```

### 10.3 Production (VPS — CI/CD via GitHub Actions)

```
main branch push
    │
    ▼ (.github/workflows/deploy.yml)
GitHub Actions
    ├── run tests (pytest)
    ├── build Docker images
    ├── push to registry
    └── SSH deploy to VPS Hostinger
            └── docker-compose -f infra/docker-compose.prod.yml up -d
```

### 10.4 Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Prod only | ≥32 chars; startup fails if default |
| `DATABASE_URL` | Always | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Always | `redis://host:6379/0` |
| `MINIO_ENDPOINT` | Always | `host:port` — no `http://` prefix |
| `MINIO_ACCESS_KEY` | Always | |
| `MINIO_SECRET_KEY` | Always | |
| `MINIO_USE_SSL` | Prod | `True` in production |
| `CORS_ORIGINS` | Prod | Comma-separated domains |
| `ANTHROPIC_API_KEY` | Optional | Only for AI report narratives |
| `DEBUG` | Dev | `False` in production triggers all security validators |

Full template: `backend/.env.example`

---

## 11. Epic & Feature Status

### MVP Epics

| # | Epic | Status | Completeness |
|---|---|---|---|
| 1 | Ingestão e Parsing | 🟡 Em andamento | 6/7 ACs |
| 2 | Motor de Validação | 🟡 Em andamento | 8/9 regras |
| 4 | Scoring de Risco | 🟡 Em andamento | MVP core ✅ |
| 5 | Dashboard e Alertas | 🟡 Em andamento | Dashboard MVP ✅ |
| 6 | Relatórios e Exportação | 🟡 Em andamento | PDF+Excel+IA ✅ |
| 7 | Multi-tenancy e Auth | 🟡 Em andamento | auth + schemas ✅ |
| 8 | Pipeline Assíncrono | 🟡 Em andamento | Celery básico ✅ |

### Completed Epics (2026-05)

| # | Epic | Completed |
|---|---|---|
| 13 | Correções Segurança e LGPD | ✅ 2026-05-26 |
| 14 | Fundação Multi-Tenancy Completa | ✅ 2026-05-26 |
| 15 | Completude Parser SPED + Cruzamento | ✅ parcial 2026-05-26 |
| 16 | Tabelas de Referência Fiscal no BD | ✅ parcial 2026-05-26 |

### Phase 2 Epics (not started)

| # | Epic | Priority |
|---|---|---|
| 3 | Detecção de Inconsistências com IA (Isolation Forest, DBSCAN) | Fase 2 |
| 9 | API Pública e Integrações ERP (SAP, TOTVS, Sankhya) | Fase 2 |
| 10 | Segurança, LGPD e Observabilidade (OpenTelemetry full) | Fase 2 |
| 17 | Performance e Escalabilidade | Em andamento |
| 18 | Observabilidade e Health Check | Em andamento |
| 11 | Onboarding, Planos e Monetização | Fase 3 |

---

## Appendix A — Domain Vocabulary

| Term | Portuguese | Description |
|---|---|---|
| `escrituracao` | Escrituração | Tax bookkeeping entry |
| `inconsistencia` | Inconsistência | Detected mismatch or anomaly |
| `divergencia` | Divergência | Value discrepancy between two sources |
| `cfop` | CFOP | Código Fiscal de Operações e Prestações (4 digits) |
| `cst` | CST | Código de Situação Tributária (2–3 digits) |
| `ncm` | NCM | Nomenclatura Comum do Mercosul (8 digits, product code) |
| `chave_acesso` | Chave de Acesso | 44-digit NF-e/CT-e unique identifier |
| `registro` | Registro SPED | SPED line type: C100, C170, C190, D100, E110, M200, M600 |
| `apuracao` | Apuração | Monthly tax calculation/settlement |
| `lote` | Lote | Batch of documents submitted together |
| `emitente` | Emitente | Document issuer (CNPJ) |
| `destinatario` | Destinatário | Document recipient (CNPJ) |

## Appendix B — Key SPED Registers

| Register | Block | Description |
|---|---|---|
| `C100` | C | NF-e header (chave, emitente, valor total, status) |
| `C110` | C | NF-e cancellation events |
| `C170` | C | NF-e line items (cfop, cst, icms, pis, cofins) |
| `C190` | C | NF-e CST/CFOP totals |
| `D100` | D | CT-e header |
| `E110` | E | ICMS monthly apuration |
| `M200` | M | PIS monthly apuration |
| `M600` | M | COFINS monthly apuration |

---

*Document maintained in `docs/SDD.md`. Update when architectural decisions change. For per-feature detail, see `docs/epics.md`. For implementation rules for AI agents, see `_bmad-output/project-context.md`.*
