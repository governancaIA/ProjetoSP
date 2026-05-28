# FiscalAI

Plataforma SaaS B2B de auditoria fiscal inteligente para o mercado brasileiro.

Detecta automaticamente inconsistências fiscais em arquivos SPED, NF-e e CT-e — antes que virem multas.

## O que faz

- **Upload e parsing** de SPED EFD ICMS/IPI, EFD Contribuições, XML NF-e e CT-e
- **Motor de regras fiscais** com 9 validações (CFOP, CST, ICMS, valor, cancelamentos, anomalias)
- **Detecção de anomalias** por Z-score sobre histórico de valores por fornecedor
- **Scoring de risco** 0–100 com estimativa de exposição financeira (base DL 1598)
- **Dashboard** com evolução 12 meses, alertas prioritários e ranking de fornecedores
- **Relatórios** em PDF executivo e Excel detalhado, com narrativa gerada por IA (Claude Haiku)
- **Multi-tenancy** via schema isolation no PostgreSQL
- **Observabilidade** com Prometheus `/metrics`, audit log LGPD e masking de PII em logs

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + FastAPI + Celery + SQLAlchemy |
| Banco | PostgreSQL (schema-per-tenant) + Redis |
| Storage | MinIO (compatível S3) |
| Frontend | React + TypeScript + Tailwind + Recharts |
| IA | Anthropic API (Claude Haiku — relatórios narrativos) |
| Deploy | Docker Compose + VPS Ubuntu (Hostinger) + nginx |

## Rodar localmente

```powershell
cd infra
docker compose up -d
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000/docs
# Flower:   http://localhost:5555
# MinIO:    http://localhost:9001
```

Ver [QUICKSTART.md](QUICKSTART.md) para setup sem Docker.

## Documentação

| Documento | Conteúdo |
|---|---|
| [QUICKSTART.md](QUICKSTART.md) | Rodar localmente |
| [DEPLOYMENT_VPS.md](DEPLOYMENT_VPS.md) | Deploy no VPS (produção) |
| [docs/epics.md](docs/epics.md) | Roadmap completo de épics |
| [docs/SDD.md](docs/SDD.md) | Software Design Document |
| [docs/arquitetura-infra.md](docs/arquitetura-infra.md) | Decisões de arquitetura |
| [infra/README.md](infra/README.md) | Variáveis e configuração de infra |
| [CLAUDE.md](CLAUDE.md) | Instruções para o Claude Code |
