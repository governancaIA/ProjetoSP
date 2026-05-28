# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Mantenha-o atualizado conforme o projeto evolui.

---

## Ambiente e Ferramentas

### Sistema Operacional
- **Shell:** PowerShell (Windows). **NÃO use bash `&` para background**; use `Start-Process` ou `Start-Job`.
- **Node.js:** Pode não estar instalado. **Sempre verificar com `node -v` antes de trabalhar no frontend**. Se ausente, solicitar instalação ao usuário ou usar `winget install nodejs`.
- **Python 3.12+:** Deve estar no PATH. Verificar com `python --version`.

### Instaladores Interativos
- **BMAD e outras ferramentas:** Se um instalador requerer input interativo (como BMAD), **NÃO execute em shells de background ou não-interativos**.
- **Ação correta:** Exiba o comando exato para o usuário executar em seu próprio terminal (ex: `bmad init`), nunca em `Start-Job` ou `&`.

### Portas Padrão
- FastAPI backend: `8000`
- Frontend Vite: `5173`
- Redis: `6379`
- PostgreSQL: `5432`
- Flower (Celery monitor): `5555`
- Sempre verificar se portas estão livres antes de iniciar servidores.

---

## Preferências de Ferramentas e Processos

### BMAD Method
- Este projeto usa BMAD para estruturação de épicos e user stories.
- **Prefer invocar BMAD diretamente** em vez de criar documentos de planejamento paralelos.
- Exemplo: Se solicitado "crie épicos para a feature X", usar `bmad` em vez de criar um doc ad-hoc.

### Agents e Exploration
- Use Agent tool com explore agent **apenas se a busca for realmente aberta** (exploração de bases de código desconhecidas, múltiplas rodadas de grep/read necessárias).
- Para tarefas diretas (ler um arquivo, fazer uma mudança específica), **prefira ferramentas diretas** (Read, Edit, Glob, Grep) em vez de spawn agents.

### Leitura e Escrita de Arquivos
- **Sempre Read um arquivo existente antes de Edit/Write**, especialmente em `docs/` (epics.md, arquitetura.md, etc.).
- Se o arquivo tiver conteúdo anterior, **mostre um merge plan ou diff mental antes de escrever**, para preservar work-in-progress.
- Exceção: novos arquivos podem ser criados diretamente com Write (sem Read prévio).

---

## Identidade do Produto

**Nome:** FiscalAI
**Categoria:** Plataforma SaaS B2B de auditoria fiscal inteligente
**Mercado:** Brasil — empresas obrigadas a SPED, NF-e, CT-e, EFD Contribuições
**Proposta de valor:** Detectar automaticamente inconsistências fiscais antes que se tornem multas — reduzindo risco, custo operacional e dependência de mão de obra especializada.

---

## Problema Central

Empresas brasileiras sofrem com:
- NFs escrituradas com valores divergentes do XML original
- Notas canceladas ainda registradas no SPED
- Notas de saída sem lançamento correspondente
- CT-es cancelados indevidamente escriturados
- Divergência de impostos (ICMS, PIS, COFINS, IPI) entre SPED e XML
- Auditoria 100% manual, cara e lenta
- Multas fiscais altíssimas por inconsistências evitáveis

---

## Stack Técnica

### Backend
- **Linguagem:** Python 3.12+
- **Framework:** FastAPI
- **Task Queue:** Celery + Redis
- **Banco principal:** PostgreSQL (multi-tenant via schema isolation)
- **Cache:** Redis
- **ORM:** SQLAlchemy + Alembic (migrations)

### IA / ML
- Anomaly detection (Isolation Forest, DBSCAN)
- ML supervisionado para classificação de inconsistências
- Motores heurísticos baseados em regras fiscais brasileiras
- LLMs (via Anthropic API) apenas para: geração de relatórios narrativos e busca contextual via RAG
- Embeddings: sentence-transformers ou OpenAI embeddings

### Infra
- Docker + Docker Compose (dev)
- Kubernetes (produção)
- Arquitetura orientada a eventos (event-driven)
- Observabilidade: OpenTelemetry + Grafana + Prometheus

### Frontend
- React + TypeScript
- Tailwind CSS
- shadcn/ui (componentes)
- Recharts (dashboards)

---

## Estrutura de Pastas (resumo)

```
backend/app/
├── core/          ← config, database, middleware (TenantMiddleware), celery, logging
├── models/        ← SQLAlchemy ORM (FiscalDocument, CTDocument, User, RuleLog)
├── schemas/       ← Pydantic request/response
├── parsers/       ← detector.py + parsers por tipo (sped, nfe, cte)
├── validators/rules/ ← BaseRule, RuleDAG (Kahn), RuleRegistry, fiscal_rules.py
├── services/      ← lógica de negócio (auth, document, storage, scoring, report)
├── api/           ← routers FastAPI (deps.py tem get_db com SET search_path)
└── tasks/         ← Celery tasks (parse_document, validate_document)

frontend/src/
├── pages/         ← telas (Dashboard, Documents, DocumentDetail, Login, Reports)
├── components/    ← por feature: ui/ (shadcn), dashboard/, documents/, document-detail/
├── hooks/         ← custom hooks (useDocuments, usePeriodScore, useAlertQueue, useJobPolling)
├── contexts/      ← AuthContext (JWT + tenant_id, persiste em localStorage)
├── services/api.ts ← axios client, todas as chamadas HTTP
└── types/         ← api.ts, auth.ts

infra/
├── docker-compose.yml      ← dev (PostgreSQL, Redis, MinIO, backend, frontend, Celery, Flower)
└── docker-compose.prod.yml ← produção
```

---

## Convenções de Código

### Python
- Formatação: `black` + `isort`
- Linting: `ruff`
- Type hints obrigatórios em todas as funções públicas
- Docstrings em português para lógica de domínio fiscal
- Testes com `pytest` + `pytest-asyncio`

### Commits
- Padrão: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`)
- Sempre referenciar a epic: `feat(epic-2): adiciona validação de CFOP`

### Nomenclatura de Domínio
- Use os termos corretos do domínio fiscal BR:
  - `sped_fiscal`, `efd_contribuicoes`, `nfe`, `cte`
  - `cfop`, `cst`, `icms`, `pis`, `cofins`, `ipi`
  - `inconsistencia`, `divergencia`, `escrituracao`
  - `registro` (linha do SPED, ex: `C100`, `C170`, `D100`)

---

## Domínio Fiscal — Contexto Essencial

### Arquivos Fiscais
| Arquivo | Descrição |
|---|---|
| SPED Fiscal (EFD ICMS/IPI) | Escrituração fiscal de entradas e saídas |
| EFD Contribuições | PIS e COFINS |
| XML NF-e | Nota Fiscal Eletrônica em XML |
| XML CT-e | Conhecimento de Transporte Eletrônico |

### Registros SPED mais críticos
- `C100` — cabeçalho da NF-e
- `C170` — itens da NF-e
- `C190` — totalização por CST/CFOP
- `D100` — CT-e
- `E110` — apuração ICMS
- `M200` / `M600` — apuração PIS/COFINS

### Inconsistências mais comuns (prioridade de detecção)
1. Valor da NF-e no SPED ≠ valor no XML
2. NF-e cancelada ainda escriturada
3. NF-e de saída sem lançamento
4. CT-e cancelado ainda no SPED
5. ICMS calculado diferente entre SPED e XML
6. CFOP incompatível com tipo de operação
7. CST inexistente para o regime tributário da empresa

---

## Epics do Projeto

Consulte `docs/epics.md` para detalhes completos.

| # | Epic | Status | Prioridade |
|---|---|---|---|
| 1 | Ingestão e Parsing de Arquivos Fiscais | 🟡 Em andamento (6/7 ACs) | MVP |
| 2 | Motor de Validação e Regras Fiscais | 🟡 Em andamento (8/9 regras) | MVP |
| 3 | Detecção de Inconsistências com IA | 🔲 Não iniciada | Fase 2 |
| 4 | Scoring de Risco Fiscal | 🟡 Em andamento (MVP core ✅) | MVP |
| 5 | Dashboard Executivo e Alertas | 🟡 Em andamento (Dashboard MVP ✅) | MVP |
| 6 | Relatórios e Exportação | 🟡 Em andamento (PDF+Excel+IA ✅) | MVP |
| 7 | Multi-tenancy e Autenticação | 🟡 Em andamento (auth + schemas ✅) | MVP |
| 8 | Pipeline Assíncrono e Escalabilidade | 🟡 Em andamento (Celery básico ✅) | MVP |
| 9 | API Pública e Integrações ERP | 🔲 Não iniciada | Fase 2 |
| 10 | Segurança, LGPD e Observabilidade | 🟡 Em andamento (fundação ✅) | Fase 2 |
| 11 | Onboarding, Planos e Monetização | 🔲 Não iniciada | Fase 3 |
| 13 | Correções Segurança e LGPD | ✅ Concluída (2026-05-26) | Crítico |
| 14 | Fundação Multi-Tenancy Completa | ✅ Concluída (2026-05-26) | Alto |
| 15 | Completude Parser SPED + Cruzamento | ✅ Concluída parcial (2026-05-26) | Alto |
| 16 | Tabelas de Referência Fiscal no BD | ✅ Concluída parcial (2026-05-26) | Alto |
| 17 | Performance e Escalabilidade | 🟡 Em andamento (streaming ✅) | Alto |
| 18 | Observabilidade e Health Check | 🟡 Em andamento (health+logs ✅) | Médio |

---

## Sprint Atual (referência: `.github/copilot-instructions.md`)

| Sprint | Objetivo | Status |
|---|---|---|
| **A** | Upload Frontend (UploadZone, progresso, polling) | 🟡 Em progresso |
| **B** | Backend fixes (CteCanceladoRule tabela, N+1 queries, Alembic migrations) | 🟡 Em progresso |
| **C** | Relatórios PDF/Excel (ReportService, endpoints, Celery async) | 🔴 Planejado |

**Critério de aceite do Sprint A:** usuário arrasta SPED.txt → barra de progresso → documento na lista com score.  
**Critério de aceite do Sprint B:** sem ERRORs nos logs; `GET /documents` com 50 docs < 500ms.

---

## Roadmap

### MVP — 30 dias
- Upload e parsing de SPED + XML NF-e
- Motor de regras com as 7 inconsistências prioritárias
- Dashboard básico com lista de inconsistências
- Relatório exportável em PDF

### Beta — 90 dias
- IA para detecção de anomalias e scoring de risco
- Multi-tenancy completo
- Pipeline assíncrono para arquivos grandes
- Alertas por e-mail

### Escala — 180 dias
- API pública com documentação
- Integrações com ERPs (SAP, TOTVS, Sankhya)
- Parceiros contábeis (modelo de revenda)
- Análise preditiva de risco futuro

---

## Guia de Desenvolvimento

### Iniciando o projeto

#### Backend
```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

#### Frontend
```powershell
cd frontend
node --version  # verificar se Node.js está instalado
npm install
npm run dev
```

#### Stack Completa (Docker)
```powershell
cd infra
docker-compose up -d
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# Flower: http://localhost:5555
```

### Testes e Linting

#### Backend — rodar todos os testes
```powershell
cd backend
pytest tests/ -v
```

#### Backend — rodar um único arquivo de teste
```powershell
cd backend
pytest tests/unit/test_fiscal_rules.py -v
```

#### Backend — rodar testes com cobertura
```powershell
cd backend
pytest tests/ --cov=app --cov-report=term-missing
```

#### Backend — linting
```powershell
cd backend
ruff check app/
black --check app/
```

#### Frontend — linting
```powershell
cd frontend
npm run lint
```

#### Frontend — build de produção
```powershell
cd frontend
npm run build
```

### Adicionando fixtures de teste
Coloque arquivos de teste em `backend/tests/fixtures/`:
- EFD samples em `.TXT`
- XML NFe/CTe em `.xml`
- Dados JSON em `.json`

Referencie em testes usando o fixture `fixtures_dir` do conftest:
```python
def test_parse_efd(fixtures_dir):
    efd_file = fixtures_dir / "1 - EFD-ICMSIPI-JAN2018.TXT"
```

---

## Arquitetura — Padrões Não Óbvios

### Fluxo de Multi-tenancy
O isolamento de tenant funciona em duas etapas que dependem uma da outra:
1. `TenantMiddleware` (`app/core/middleware.py`) decodifica o JWT e coloca `tenant_id` em `request.state.tenant_id`. **Não abre sessão de banco.**
2. `get_db()` em `api/deps.py` lê `request.state.tenant_id` e executa `SET search_path = <tenant_id>, public` na sessão SQLAlchemy antes de yieldar.

Resultado: todas as queries de um request rodam no schema do tenant automaticamente. Rotas públicas (login, register, health) estão em `_SKIP_PATHS` no middleware.

### Motor de Regras (DAG)
As regras fiscais em `validators/rules/fiscal_rules.py` são executadas via `RuleDAG` (`validators/rules/dag.py`) usando o algoritmo de Kahn para ordenação topológica. Cada `BaseRule` declara `depends_on` para garantir que pré-condições rodem antes. O `RuleRegistry` (`validators/rules/registry.py`) instancia e registra as regras.

Para adicionar uma nova regra: subclasse `BaseRule`, implemente `execute()`, declare `rule_id` e `depends_on`, e registre em `registry.py`.

### Pipeline Upload → Parse → Validate → Score
```
POST /api/v1/uploads/
  → StorageService (stream para MinIO/S3)
  → Celery task: parse_document (detector de formato → parser correto)
  → Celery task: validate_document (RuleDAG + ScoringService)
  → resultado persistido em FiscalDocument + RuleLog
```
O frontend faz polling via `GET /api/v1/jobs/{job_id}` a cada 2s até status `completed` ou `failed`.

### Scoring de Risco
`ScoringService` (`services/scoring_service.py`) calcula score 0–100 por documento e por período. Níveis: `CRITICAL` (0–24), `HIGH` (25–49), `MEDIUM` (50–74), `LOW` (75–100). Penalidades baseadas em DL 1598 para estimativa de multa.

### API
Todos os endpoints usam o prefixo `/api/v1/`. Routers registrados em `app/main.py`: auth, uploads, documents, validation, jobs, reports. O Swagger está em `/docs` (desabilitado em produção via configuração).

### Estrutura de Logging
`app/core/logging_config.py` configura JSON structured logging (python-json-logger). `LogContext` em middleware propaga `tenant_id` para todos os logs do request. **LGPD: nunca logar CNPJ ou valores fiscais em texto plano.**

---

## Regras para o Claude Code

1. **Sempre pergunte antes de criar novos módulos** que não estão na estrutura de pastas definida
2. **Nunca remova validações fiscais** sem confirmar com o usuário
3. **Testes são obrigatórios** para qualquer lógica do motor de regras (`validators/`)
4. **Documente decisões de arquitetura** em `docs/adr/` quando fizer escolhas relevantes
5. **Use os termos do domínio** definidos na seção de nomenclatura acima
6. **Atualize a tabela de epics** em `docs/epics.md` quando uma epic for concluída
7. **LGPD:** nenhum dado fiscal do cliente deve ser logado em texto plano — sempre mascarar CNPJ e valores em logs
8. **Imports de fixtures:** use `backend/tests/fixtures/` para test data, NÃO `docs/`