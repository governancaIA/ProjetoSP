# CLAUDE.md — FiscalAI

> Este arquivo é lido automaticamente pelo Claude Code em toda sessão.
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

## Estrutura de Pastas

```
fiscalai/
├── README.md
├── CLAUDE.md                  ← este arquivo
├── .gitignore                 ← commit obrigatório
│
├── docs/                      ← Documentação do projeto
│   ├── epics.md               ← épicos e user stories
│   ├── arquitetura-infra.md   ← decisões de arquitetura (ADRs)
│   ├── adr/                   ← Architecture Decision Records
│   │   └── README.md
│   ├── 1 - EFD-ICMSIPI-JAN2018.TXT
│   ├── 2 - EFD-ICMSIPI-FEV2018.TXT
│   └── 3 - EFD-ICMSIPI-MAR2018.TXT
│
├── backend/
│   ├── README.md
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example           ← template de variáveis
│   ├── .env.production        ← produção (git ignore)
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            ← entrada FastAPI
│   │   │
│   │   ├── core/              ← config, segurança, database
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── database.py
│   │   │   └── celery_app.py
│   │   │
│   │   ├── models/            ← SQLAlchemy ORM
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── fiscal_document.py
│   │   │   ├── ct_document.py
│   │   │   ├── document.py
│   │   │   └── rule_log.py
│   │   │
│   │   ├── schemas/           ← Pydantic request/response
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   └── documents.py
│   │   │
│   │   ├── exceptions/        ← custom exceptions (futuro)
│   │   │   └── __init__.py
│   │   │
│   │   ├── parsers/           ← parsers de arquivos
│   │   │   ├── __init__.py
│   │   │   ├── detector.py
│   │   │   ├── sped_efd_icms.py
│   │   │   ├── nfe_xml.py
│   │   │   └── cte_xml.py
│   │   │
│   │   ├── validators/        ← motor de regras fiscais
│   │   │   ├── __init__.py
│   │   │   └── rules/
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── dag.py
│   │   │       ├── registry.py
│   │   │       └── fiscal_rules.py
│   │   │
│   │   ├── ai/                ← detecção de anomalias, scoring (futuro)
│   │   │   ├── __init__.py
│   │   │   └── ...
│   │   │
│   │   ├── services/          ← lógica de negócio
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── document_service.py
│   │   │   ├── rule_service.py
│   │   │   ├── scoring_service.py
│   │   │   └── storage_service.py
│   │   │
│   │   ├── api/               ← rotas FastAPI
│   │   │   ├── __init__.py
│   │   │   ├── deps.py        ← dependencies
│   │   │   ├── auth.py
│   │   │   ├── uploads.py
│   │   │   ├── documents.py
│   │   │   └── validation.py
│   │   │
│   │   └── tasks/             ← Celery tasks
│   │       ├── __init__.py
│   │       ├── parse_document.py
│   │       └── validate_document.py
│   │
│   ├── migrations/            ← Alembic DB migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── fixtures/          ← EFD samples, test data
│   │   │   ├── __init__.py
│   │   │   ├── 1 - EFD-ICMSIPI-JAN2018.TXT
│   │   │   ├── 2 - EFD-ICMSIPI-FEV2018.TXT
│   │   │   └── 3 - EFD-ICMSIPI-MAR2018.TXT
│   │   ├── unit/
│   │   └── integration/
│   │
│   └── Dockerfile
│
├── frontend/
│   ├── README.md
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── .env.example           ← template de variáveis
│   │
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   │
│   │   ├── pages/             ← telas
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── DocumentsPage.tsx
│   │   │   ├── DocumentDetailPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── ReportsPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   │
│   │   ├── components/        ← componentes por feature
│   │   │   ├── ui/            ← componentes primitivos (shadcn)
│   │   │   ├── layout/        ← layout compartilhado
│   │   │   ├── dashboard/     ← componentes do dashboard
│   │   │   ├── documents/     ← componentes de documentos
│   │   │   └── document-detail/ ← detalhes do documento
│   │   │
│   │   ├── hooks/             ← custom React hooks
│   │   │   ├── usePeriodScore.ts
│   │   │   ├── useAlertQueue.ts
│   │   │   ├── useDocuments.ts
│   │   │   ├── useDocumentScore.ts
│   │   │   └── useValidationResults.ts
│   │   │
│   │   ├── contexts/          ← React contexts
│   │   │   └── AuthContext.tsx
│   │   │
│   │   ├── services/          ← chamadas de API
│   │   │   └── api.ts
│   │   │
│   │   ├── lib/               ← utilitários
│   │   │   ├── utils.ts
│   │   │   └── constants.ts   ← (futuro)
│   │   │
│   │   ├── types/             ← TypeScript types
│   │   │   ├── api.ts
│   │   │   └── auth.ts
│   │   │
│   │   └── __tests__/         ← testes colocalizados (futuro)
│   │       ├── components/
│   │       └── hooks/
│   │
│   ├── public/                ← assets estáticos
│   │   └── favicon.ico
│   │
│   ├── Dockerfile
│   ├── Dockerfile.prod
│   └── nginx.conf
│
├── infra/                     ← Toda infraestrutura e deployment
│   ├── README.md
│   ├── docker-compose.yml     ← dev environment
│   ├── docker-compose.prod.yml ← produção
│   │
│   ├── docker/                ← Dockerfiles centralizados (futuro)
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   └── .dockerignore
│   │
│   ├── scripts/               ← scripts de setup
│   │   └── setup-easypanel.ps1
│   │
│   ├── k8s/                   ← Kubernetes (futuro)
│   │   └── .gitkeep
│   │
│   └── terraform/             ← IaC (futuro)
│       └── .gitkeep
│
├── scripts/                   ← scripts de utilidade
│   ├── dev-setup.ps1         ← setup automático local (futuro)
│   ├── lint.sh               ← linting (futuro)
│   └── test.sh               ← execução de testes (futuro)
│
└── .github/                  ← CI/CD (futuro)
    ├── workflows/
    │   ├── test.yml          ← testes
    │   └── deploy.yml        ← deployment
    └── CODEOWNERS
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
| 1 | Ingestão e Parsing de Arquivos Fiscais | 🔲 Não iniciada | MVP |
| 2 | Motor de Validação e Regras Fiscais | 🔲 Não iniciada | MVP |
| 3 | Detecção de Inconsistências com IA | 🔲 Não iniciada | MVP |
| 4 | Scoring de Risco Fiscal | 🔲 Não iniciada | MVP |
| 5 | Dashboard Executivo e Alertas | 🔲 Não iniciada | MVP |
| 6 | Relatórios e Exportação | 🔲 Não iniciada | MVP |
| 7 | Multi-tenancy e Autenticação | 🔲 Não iniciada | MVP |
| 8 | Pipeline Assíncrono e Escalabilidade | 🔲 Não iniciada | Fase 2 |
| 9 | API Pública e Integrações ERP | 🔲 Não iniciada | Fase 2 |
| 10 | Segurança, LGPD e Observabilidade | 🔲 Não iniciada | Fase 2 |
| 11 | Onboarding, Planos e Monetização | 🔲 Não iniciada | Fase 3 |

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

### Adicionando fixtures de teste
Coloque arquivos de teste em `backend/tests/fixtures/`:
- EFD samples em `.TXT`
- XML NFe/CTe em `.xml`
- Dados JSON em `.json`

Referencie em testes:
```python
def test_parse_efd(fixtures_dir):
    efd_file = fixtures_dir / "1 - EFD-ICMSIPI-JAN2018.TXT"
```

### Movendo Dockerfiles (Próximas Fases)

Eventualmente, Dockerfiles serão centralizados em `infra/docker/`:
```
# De:
backend/Dockerfile
frontend/Dockerfile
frontend/Dockerfile.prod

# Para:
infra/docker/backend.Dockerfile
infra/docker/frontend.Dockerfile
infra/docker/frontend.prod.Dockerfile
```

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