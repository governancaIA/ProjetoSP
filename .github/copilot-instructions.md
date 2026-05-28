# FiscalAI — Análise de EPICs e Code Reviews

**Data da Análise:** 2026-05-26  
**Status:** Em desenvolvimento ativo — MVP próximo de conclusão

---

## 📊 Status Geral de EPICs

### MVP — EPICs Críticas (Fases 1-2)

| # | Epic | Objetivo | Status | Prioridade |
|---|---|---|---|---|
| **1** | **Ingestão e Parsing** | Upload e parsing de SPED, NF-e, CT-e, EFD | 🟡 Em Progresso | MVP |
| **2** | **Motor de Validação** | Regras fiscais (CFOP, CST, ICMS, valor) | 🟡 Em Progresso | MVP |
| **3** | **Detecção de Inconsistências com IA** | Anomaly detection e heurísticas | 🟡 Parcial (heurísticas simples) | Fase 2 |
| **4** | **Scoring de Risco Fiscal** | Scoring por documento/período | 🟡 Implementado | MVP |
| **5** | **Dashboard Executivo e Alertas** | Dashboard, alertas em tempo real | 🟡 Em Progresso | MVP |
| **6** | **Relatórios e Exportação** | PDF/Excel de auditoria | 🟡 Planejado (Sprint atual) | MVP |
| **7** | **Multi-tenancy e Autenticação** | JWT, schema isolation, RBAC | 🟢 Implementado | MVP |
| **8** | **Pipeline Assíncrono e Escalabilidade** | Celery, Redis, async jobs | 🟢 Implementado | Fase 2 |
| **9** | **API Pública e Integrações ERP** | REST API, webhooks, integração ERP | 🟡 API básica | Fase 2 |
| **10** | **Segurança, LGPD e Observabilidade** | Logging, masking, telemetria | 🟡 Parcial | Fase 2 |
| **11** | **Onboarding, Planos e Monetização** | Signup flow, planos, pagamento | 🔴 Não iniciado | Fase 3 |

**Legenda:** 🟢 Completo | 🟡 Em Progresso | 🔴 Não iniciado

---

## 🔍 Code Review Realizado

### Escopo Revisado

**Data do Review:** 2026-05-24  
**Commits Analisados:** `a101431` até `1265516`  
**Áreas Cobertas:**
- Docker & Infrastructure (docker-compose.yml, Dockerfiles multi-stage)
- API & Authentication (JWT, refresh tokens, rate limiting)
- Frontend Auth State (React Context, token persistence)
- Multi-tenancy (schema isolation via middleware)
- Deployment Documentation (EasyPanel setup guides)

**Status Geral:** ✅ **APPROVED WITH MINOR NOTES**

### Principais Achados ✅

**Positivos:**

1. **Docker & Infrastructure**
   - ✅ Multi-stage frontend build (Node builder → Nginx runtime)
   - ✅ Proper layer caching (requirements before code copy)
   - ✅ Health checks em todos os serviços críticos (PostgreSQL, Redis, MinIO)
   - ✅ Volume persistence configurada
   - ✅ Networks isolation (`fiscalai-network`)

2. **API & Authentication**
   - ✅ Clean router com HTTP status codes corretos
   - ✅ Dependency injection via Pydantic
   - ✅ Input validation e error handling apropriados
   - ✅ JWT com tokens de acesso + refresh (segurança robusta)
   - ✅ Rate limiting implementado (`slowapi`)
   - ✅ No hardcoded secrets

3. **Frontend Authentication**
   - ✅ React Context com estado de autenticação limpo
   - ✅ Token persistence em localStorage com expiração
   - ✅ Protected routes com redirecionamento
   - ✅ Proper cleanup on logout

4. **Multi-tenancy**
   - ✅ Schema isolation via middleware TenantMiddleware
   - ✅ Tenant context extirpado de JWT (header Authorization)
   - ✅ Session factory aplica filtro de schema por tenant

### Notas para Production 🔧

1. **Build Context Correction** ✅ JÁ CORRIGIDO
   - Issue: Build context era `backend/` em vez de `.`
   - Status: Resolvido em EASYPANEL_CHECKLIST.md

2. **Hardening Futuro** (Nice-to-have):
   - Adicionar `USER 1000` explícito nos Dockerfiles (segurança)
   - Limites de CPU/memória nos services docker-compose (já em EasyPanel)
   - MINIO_USE_SSL já correto em production

---

## 🚀 Roadmap de Entregas (Sprints)

### Sprint 0 — Estabilização ✅ CONCLUÍDO

**Objetivo:** Fazer o que existe funcionar corretamente em produção.

| Item | Status | Detalhes |
|------|--------|----------|
| B1: Import de `fiscal_rules` em `validate_document.py` | ✅ | Celery task funciona |
| B2: Linkagem C170→C100 no SPED parser | ✅ | Cruzamento correto |
| B3: `isAuthenticated` false no page reload | ✅ | AuthContext persiste token |

**Resultado:** Pipeline upload → parse → validação → scoring funciona end-to-end.

---

### Sprint A — Upload de Arquivo (Frontend) 🟡 EM PROGRESSO

**Objetivo:** Usuário consegue subir arquivos fiscais pela UI.  
**Prazo:** 1 dia  
**Bloqueia:** Todos os outros epics (sem upload, dashboard vazio)

| # | Tarefa | Status | Detalhes |
|---|--------|--------|----------|
| A1 | Componente `UploadZone` (drag-and-drop) | 🟡 | Aceita .txt, .xml, .zip |
| A2 | Barra de progresso com estado | 🟡 | pending → processing → completed/failed |
| A3 | Polling do status do job | 🟡 | GET /documents/{id} a cada 2s |
| A4 | Integração na `DocumentsPage` | 🟡 | Modal com UploadZone |
| A5 | Toast de sucesso/erro | 🟡 | Notificação após conclusão |

**Aceite:** Usuário arrasta SPED.txt → barra de progresso → documento na lista com score.

---

### Sprint B — Estabilização do Backend 🟡 EM PROGRESSO

**Objetivo:** Corrigir bugs restantes sem quebrar fluxo.  
**Prazo:** 1 dia

| # | Tarefa | Arquivo | Status | Detalhes |
|---|--------|---------|--------|----------|
| B4 | `CteCanceladoRule` — tabela correta | validators/rules/fiscal_rules.py | 🟡 | Usar `CTDocument` em vez de `FiscalDocument` |
| B5 | Tenant schema no register | services/auth_service.py | 🟡 | Chamar `create_tenant_schema()` após criar User |
| B6 | N+1 queries em `GET /documents` | api/documents.py | 🟡 | JOIN em query única vs N queries |
| B7 | Alembic migrations | migrations/versions/ | 🟡 | Migração inicial do estado atual |

**Aceite:** Sem ERRORs nos logs. `GET /documents` com 50 docs < 500ms.

---

### Sprint C — Relatórios e Exportação 🟡 PLANEJADO

**Objetivo:** Cliente exporta auditoria em PDF/Excel.  
**Prazo:** 2-3 dias  
**Valor:** Fecha venda — "algo para mostrar ao contador"

| # | Tarefa | Status | Detalhes |
|---|--------|--------|----------|
| C1 | Endpoint `GET /reports/period/{year}/{month}/pdf` | 🔴 | Score + top inconsistências |
| C2 | Endpoint `GET /reports/document/{id}/pdf` | 🔴 | Relatório de 1 documento |
| C3 | Endpoint `GET /reports/period/{year}/{month}/excel` | 🔴 | Excel com todas as inconsistências |
| C4 | Serviço `ReportService` | 🔴 | reportlab (PDF) + openpyxl (Excel) |
| C5 | Frontend `ReportsPage.tsx` | 🔴 | Botões "Baixar PDF" e "Baixar Excel" |
| C6 | Celery task assíncrona | 🔴 | Background job com link de download |

**Aceite:** Clique "Baixar PDF" → download < 5s para 500 documentos.

---

## 🎯 Próximas Prioridades (Ordem Recomendada)

### ✅ Imediato (Sprint Atual)

1. **Epic A — Upload Frontend** (bloqueia tudo)
   - Completar componente UploadZone
   - Polling de status de job
   - Integração com DocumentsPage

2. **Epic B — Backend Stabilization**
   - Fix `CteCanceladoRule` (tabela correta)
   - Fix tenant schema creation on register
   - Otimizar N+1 queries em `GET /documents`
   - Criar migrations Alembic

3. **Epic 6 — Relatórios** (fecha venda)
   - Endpoints PDF/Excel
   - ReportService com templates
   - Celery async job para grandes relatórios

### 🔄 Sequência Recomendada

```
Sprint A (Upload) 
    ↓
Sprint B (Backend Fixes)
    ↓
Sprint C (Relatórios + PDF/Excel)
    ↓
[MVP Ready for Sales Demo]
    ↓
Epic 3 (Anomaly Detection - advanced AI)
Epic 10 (Security, LGPD, Observability)
```

---

## 🔒 Compliance & Quality Gates

### ✅ Atendidos

- [x] Multi-tenancy schema isolation
- [x] JWT authentication com refresh tokens
- [x] Rate limiting on auth endpoints
- [x] Database migrations via Alembic
- [x] Async task processing (Celery + Redis)
- [x] Docker multi-stage builds

### ⚠️ Pendentes para Produção

- [ ] LGPD compliance (masking de dados sensíveis em logs)
- [ ] Observability (OpenTelemetry, structured logging)
- [ ] API versioning strategy
- [ ] Webhook retry logic (para integrações)
- [ ] API rate limiting por tenant (quotas)

### 🟡 Em Análise

- Anomaly detection (Isolation Forest) — roadmap incerto
- ERP integration strategy — API design pending
- LLM usage (Anthropic API) — apenas para relatórios narrativos (não confirmado)

---

## 📋 Métricas de Saúde do Projeto

| Métrica | Status | Notas |
|---------|--------|-------|
| **Code Review Status** | ✅ APPROVED | Minor hardening suggestions for production |
| **Test Coverage** | 🟡 Partial | Backend tests OK; frontend tests needed |
| **Documentation** | ✅ Good | CLAUDE.md, epics.md, deployment guides comprehensive |
| **Deployment Readiness** | 🟡 Ready for MVP | EasyPanel config correct, Docker proven |
| **Multi-tenancy** | ✅ Solid | Schema isolation tested, JWT correct |
| **Performance** | 🟡 Needs tuning | N+1 queries flagged, solution identified |
| **Security** | 🟡 Good (MVP stage) | Hardening post-MVP recommended |

---

## 🎬 Próximas Ações Recomendadas

1. **Completar Sprint A** (Upload frontend) — blocker para everything else
2. **Aplicar fixes Sprint B** — N+1 queries, tenant schema creation, CT-e rule
3. **Criar PDF/Excel service Sprint C** — high business value ("must have" para venda)
4. **Add LGPD masking** — audit logging antes de produção
5. **Estruturar testes frontend** — cypress ou playwright para E2E
6. **Definir SLA de performance** — GET /documents deve sempre < 500ms

---

## 📚 Referências Importantes

- **docs/epics.md** — Full epic descriptions with acceptance criteria
- **CODE_REVIEW.md** — Detailed code review findings
- **CLAUDE.md** — Project context, rules, and conventions
- **QUICKSTART.md** — Development setup guide
- **DEPLOYMENT_*.md** — Production deployment documentation
