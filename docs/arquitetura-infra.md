# Arquitetura de Infraestrutura — FiscalAI MVP

**Criado:** 2026-05-24 | **Atualizado:** 2026-05-28  
**Status:** MVP implementado e rodando em produção  
**Stack:** PostgreSQL (schema-per-tenant) + MinIO + Celery + Redis + Caddy  
**Custo atual:** ~$0 (VPS Hostinger existente)  
**Escalabilidade:** 50–100 clientes em 1 VPS; migração para DB-per-tenant em ~2–3 sprints  

## Produção atual

| Componente | Valor |
|---|---|
| VPS | Hostinger — `89.116.214.246` |
| Domínio | `adriner.fr` (DNS A → VPS IP) |
| Reverse proxy | Caddy 2 (TLS automático via Let's Encrypt) |
| Compose file | `infra/docker-compose.prod.yml` |
| Acesso Flower | SSH tunnel: `ssh -L 5555:127.0.0.1:5555 root@89.116.214.246` |
| Acesso MinIO console | SSH tunnel: `ssh -L 9001:127.0.0.1:9001 root@89.116.214.246` |



---

## 1. DECISÃO FINAL: ARQUITETURA EM 3 CAMADAS

### Camada 1: Storage (Arquivos Fiscais)
**Escolha:** MinIO local em Docker container na VPS Hostinger  

**Decisão por:**
- ✅ **Custo:** Zero adicional (já paga VPS)
- ✅ **Segurança:** TLS + Basic Auth; dados locais (sem dependência externa)
- ✅ **Escalabilidade:** Suporta 50–100 clientes com uploads até 2GB
- ⚠️ **Limite:** Crescimento disco limitado ao plano VPS (monitora espaço)
- 🔄 **Migração para S3:** Código já abstrato via `boto3`; zero quebra de app

**Modelo escalável:**
```
MVP (1–6 meses):  MinIO na VPS (docker-compose)
               ↓
Fase 2 (6–12m):   Migra S3 via boto3 (sem mudar código Python)
               ↓
Enterprise:       S3 + CloudFront (multi-region replication)
```

---

### Camada 2: Processamento Assíncrono (Parsing, Validação)
**Escolha:** Celery + Redis em containers na VPS  

**Decisão por:**
- ✅ **Custo:** Zero adicional
- ✅ **Segurança:** Runs local; fila em-memória criptografada
- ✅ **Escalabilidade:** Suporta 50–100 clientes (4 workers Celery = ~100 jobs/min)
- ⚠️ **Limite:** CPU/RAM da VPS; requer monitoramento (Flower)
- 🔄 **Migração para SQS:** Código Python já agnóstico (trocar broker Redis → SQS URL)

**Resource allocation na VPS:**
```
FastAPI (API server)      → 1 core / 1GB RAM
Celery workers (4x)       → 2 cores / 2GB RAM
Redis                     → 256MB (em-memória)
PostgreSQL                → 1 core / 2GB RAM
─────────────────────────────────────────
Total esperado:           4 cores / 5.2GB RAM
(VPS Hostinger: verifica se suporta ~8 cores / 8GB)
```

---

### Camada 3: Banco de Dados (Multi-Tenancy)
**Escolha:** PostgreSQL (schema-per-tenant) na VPS existente  

**Decisão por:**
- ✅ **Custo:** Zero adicional (já usa PostgreSQL)
- ✅ **Segurança:** Isolamento máximo; schemas separados; RLS habilitado
- ✅ **Escalabilidade:** Suporta 50+ tenants em 1 instância (esperado: ~5–10 schemas ativos em MVP)
- ⚠️ **Limite:** Conexões PostgreSQL (max_connections); crescimento índices
- 🔄 **Migração para database-per-tenant:** Código prepara-se via abstração de tenant router

**Padrão de schema:**

```sql
-- Shared (public schema)
CREATE SCHEMA public;
CREATE TABLE public.organizations (org_id, name, plan, status);
CREATE TABLE public.users (user_id, org_id, email, role);

-- Per-tenant (isolado)
CREATE SCHEMA tenant_org_001;
  CREATE TABLE tenant_org_001.documents (doc_id, tenant_id, file_hash, ...);
  CREATE TABLE tenant_org_001.fiscal_documents (fiscal_doc_id, ...);
  CREATE TABLE tenant_org_001.fiscal_items (item_id, ...);

CREATE SCHEMA tenant_org_002;
  -- ... same structure, different data
  
-- RLS enabled
ALTER TABLE tenant_org_001.documents ENABLE ROW LEVEL SECURITY;
```

**Migração futura para database-per-tenant:**
```sql
-- Quando org cresce (> 1M documentos):
CREATE DATABASE fiscal_org_123;
  -- Move schema tenant_org_001 → public em fiscal_org_123
  -- App rota: org_id → connection string (org_db_host)
  -- Fallback: small orgs mantêm schema-per-tenant no PostgreSQL compartilhado
```

---

## 2. DETALHAMENTO: CUSTO x SEGURANÇA x ESCALABILIDADE

### Comparação 3 Opções Avaliadas

| Critério | MinIO Local | S3 AWS | Filesystem |
|----------|------------|--------|------------|
| **Custo inicial** | $0 | ~$5–15/m | $0 |
| **Custo crescimento** | Disco VPS | Proporcional GB | Disco VPS |
| **Segurança** | TLS local (bom) | AWS gerenciado (ótimo) | Sem encrypt (risco) |
| **Escalabilidade** | 50–100 clientes | Ilimitada | 10–20 clientes |
| **Downtime file loss** | Depende backup VPS | Redundância AWS | Perda total disco |
| **Recomendação** | ✅ MVP | Phase 2+ | ❌ Não recomendado |

### Comparação: Celery vs APScheduler vs SQS

| Critério | Celery + Redis | APScheduler | AWS SQS |
|----------|----------------|------------|---------|
| **Custo** | $0 | $0 | ~$0.50/m |
| **Escalabilidade** | 50–100 cli / VPS | 10–20 cli / VPS | Ilimitada |
| **Robustez** | Excelente (DLQ, retry) | Básica | Excelente (AWS) |
| **Monitoring** | Flower (built-in) | Logs simples | CloudWatch |
| **Recomendação** | ✅ MVP → Fase 2 | ❌ Não | ✅ Enterprise |

### Comparação: Schema-per-tenant vs Row-level vs DB-per-tenant

| Critério | Schema-per-tenant | Row-level | DB-per-tenant |
|----------|------------------|-----------|---------------|
| **Custo** | $0 (1 PostgreSQL) | $0 | ~$30/cli/m |
| **Segurança** | Isolamento total | Risco bug filtering | Máxima |
| **Escalabilidade** | 50+ tenants / DB | ~20 tenants | Ilimitada |
| **Complejidade** | Média (router) | Baixa | Alta (muitos DBs) |
| **LGPD Compliance** | Auditável ✅ | Difícil ⚠️ | Perfeito ✅ |
| **Recomendação** | ✅ MVP → Beta | ❌ Não fiscal | ✅ Enterprise+ |

---

## 3. ARQUITETURA PROPOSTA: "ESCALÁVEL DESDE O MVP"

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (uvicorn)                        │
│  POST /uploads (drag-drop)  →  Celery Task Chain            │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼──────────────┐
    ▼            ▼              ▼
┌─────────┐ ┌────────┐ ┌──────────────┐
│ MinIO   │ │ Redis  │ │ PostgreSQL   │
│ (Files) │ │(Queue) │ │ (7 schemas)  │
└─────────┘ └────────┘ └──────────────┘
    ▲            ▲              ▲
    └────────────┼──────────────┘
          (docker-compose)
          (All on 1 VPS)
```

**Fluxo de um upload:**

```
1. Cliente: POST /uploads com SPED.txt
2. API: Valida arquivo → S3/MinIO :9000 (boto3)
3. API: Cria job → Redis queue → retorna job_id
4. Celery Worker: Pega task (detector → parser → validação)
5. Worker: Armazena em PostgreSQL (tenant_org_001 schema)
6. Worker: Notifica via WebSocket (real-time progress)
7. Cliente: Dashboard atualiza com resultados
```

---

## 4. PLANO DE ESCALAÇÃO

### MVP (Semanas 1–4)
- ✅ MinIO local na VPS
- ✅ PostgreSQL schema-per-tenant (7 schemas = 7 clientes max)
- ✅ Celery 4 workers (local)
- ✅ Custo: $0 (VPS Hostinger existente)
- ✅ Clientes: 1–5

### Beta (Semanas 5–12)
- ✅ Adiciona 2 mais PostgreSQL worker nodes? (se recursos VPS apertar)
- ✅ MinIO replicado para backup externo (Wasabi?)
- ✅ Celery escalado: 8 workers (mais CPUs alocadas)
- ✅ Custo: ~$20/m (backup Wasabi)
- ✅ Clientes: 10–30

### Fase 2 (Mês 3+)
- ✅ Migra MinIO → AWS S3 (boto3 já pronto; zero code change)
- ✅ Migra Celery → AWS SQS (broker abstrato; troca URL)
- ✅ Primeiros clients enterprise → database-per-tenant (dedicated PostgreSQL)
- ✅ Custo: ~$50–100/m (S3 + SQS + extra DBs)
- ✅ Clientes: 50–100

---

## 5. IMPLEMENTAÇÃO: CHECKLIST

> Estado em 2026-05-28 — todos os itens do MVP concluídos.

### Semana 1: Infrastructure Setup ✅
- [x] `docker-compose.yml` com: PostgreSQL, Redis, MinIO, FastAPI, Celery, Flower
- [x] `.env.example` com credenciais (MinIO, Postgres, Redis URLs)
- [x] Schema de tenant criado atomicamente no register (`create_tenant_schema()`)
- [x] Alembic migration framework com migrations 001–006

### Semana 2: Tenant Router & ORM ✅
- [x] `backend/app/core/middleware.py` — `TenantMiddleware` extrai `tenant_id` do JWT
- [x] `backend/app/api/deps.py` — `get_db()` seta `SET search_path = tenant_<id>, public`
- [x] Sanitização de `tenant_id` com regex antes de interpolação SQL (EPIC 13)
- [x] RLS habilitado em todas as tabelas por tenant

### Semana 3–4: Parsers + Celery Tasks ✅
- [x] `parsers/detector.py` — detecção automática de tipo/versão do arquivo
- [x] `parsers/sped_efd_icms.py` — blocos 0, C, D, E com C100/C170/D100/E110
- [x] `parsers/nfe_xml.py` + `parsers/cte_xml.py` — NF-e v4.0 e CT-e v3.0
- [x] `parsers/efd_contribuicoes.py` — M100/M200 (PIS/COFINS por CST)
- [x] `tasks/parse_document.py` + `tasks/validate_document.py` — Celery chain
- [x] `api/uploads.py` — upload chunked streaming, SHA-256 dedup

### Semana 5: Tests + Monitoring ✅
- [x] 84+ testes unitários para parsers, regras e scoring
- [x] Flower acessível via SSH tunnel (porta 5555 local only em prod)
- [x] Prometheus `/metrics` com métricas de request, latência e fila Celery

---

## 6. MONITORAMENTO & ALERTAS

Na VPS, rodar:

```bash
# Top commands para monitorar
docker stats                    # Memory + CPU por container
docker logs -f celery-worker    # Celery logs in real-time
psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"  # DB connections

# Flower (Celery Web UI)
http://localhost:5555

# MinIO Web UI
http://localhost:9000

# Prometheus (se add grafo)
http://localhost:9090
```

**Alertas críticos:**
- ❌ PostgreSQL conexões > 90 (max_connections breach)
- ❌ Redis memória > 90% (OOM risk)
- ❌ MinIO espaço disco < 10%
- ❌ Celery queue depth > 100 (backlog crescendo)

---

## 7. BACKUP & DISASTER RECOVERY

**Recomendações:**

1. **PostgreSQL:** 
   - `pg_dump` diário para Wasabi (S3-compatible)
   - Retenção: 30 dias

2. **MinIO (arquivos SPED/XML):**
   - Replicação para Wasabi em tempo real
   - Custo: ~$10/m para 100GB

3. **Redis (ephemeral, não persiste):**
   - Sem backup necessário; fila recalculável

4. **Teste RPO/RTO:**
   - RPO (Recovery Point Objective): 1 dia
   - RTO (Recovery Time Objective): 4 horas

---

## 8. ROADMAP DE MIGRAÇÃO PARA ENTERPRISE

Quando cliente quer:
- ✅ SLA 99.9% uptime
- ✅ Isolamento total de dados
- ✅ Conformidade PCI-DSS ou similar

**Ação:**
```
1. Cria PostgreSQL dedicado (RDS AWS, ou VM nova)
2. Migrate schema tenant_org_XXX → public no novo DB
3. App rota: org_id → connection string (default: shared | enterprise: dedicated)
4. Cliente paga ~$50–100/m pelo DB dedicado
5. Zero downtime para outros clientes
```

---

## RESUMO EXECUTIVO

| Dimensão | Escolha | Justificativa |
|----------|---------|---------------|
| **Custo MVP** | MinIO + Celery local | $0; VPS Hostinger já existe |
| **Segurança** | Schema-per-tenant + RLS | Isolamento máximo; auditável LGPD |
| **Escalabilidade** | Arquitetura agnóstica (MinIO → S3, Celery → SQS) | Zero refator ao escalar |
| **Time-to-Market** | 4 semanas MVP | Infraestrutura pronta dia 1 |
| **Custo Escala** | ~$50–100/m em Fase 2 | Crescimento linear com # clientes |

🚀 **Vamos começar implementação!**
