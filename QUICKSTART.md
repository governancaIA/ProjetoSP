# FiscalAI — Quick Start Guide

## Pré-requisitos

- **Docker Desktop** (Windows/Mac) ou **Docker + Docker Compose** (Linux)
- **PowerShell 5.0+** (Windows)
- **Git**

## Início Rápido — Levantar Tudo de Uma Vez

### 1️⃣ Stack Completa (com PostgreSQL, Redis, MinIO, Backend, Frontend, Celery, Flower)

```powershell
# Terminal (PowerShell)
.\up.ps1                    # Modo foreground (logs em tempo real)
# ou
.\up.ps1 -Detached         # Modo background
```

**Serviços que sobem automaticamente:**

| Serviço | URL | Login | Descrição |
|---------|-----|-------|-----------|
| **Frontend** | http://localhost:5173 | — | React app (Vite) |
| **Backend** | http://localhost:8000 | — | FastAPI com Swagger em `/docs` |
| **Flower** (Celery UI) | http://localhost:5555 | — | Monitoramento de tasks |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin_password | Object storage |
| **PostgreSQL** | localhost:5432 | fiscalai_user / fiscalai_password | Database |
| **Redis** | localhost:6379 | — | Cache + Message Broker |

### 2️⃣ Inicializar Banco de Dados

```powershell
# Executa Alembic migrations + cria schema de tenant
.\init-db.ps1                              # Tenant padrão: example-tenant-001
# ou com tenant customizado:
.\init-db.ps1 -TenantId "meu-cliente-001"
```

### 3️⃣ Parar a Stack

```powershell
.\down.ps1                 # Para containers
# ou
.\down.ps1 -Prune         # Para + limpa imagens/containers dangling
```

## Fluxo Completo (Primeira Vez)

```powershell
# 1. Subir stack em detached mode (background)
.\up.ps1 -Detached

# Aguardar ~30s para todos os containers ficarem saudáveis
Start-Sleep -Seconds 30

# 2. Inicializar banco
.\init-db.ps1

# 3. Verificar saúde dos serviços
docker-compose -f docker-compose.prod.yml ps

# 4. Acessar:
#    - Frontend: http://localhost:5173
#    - Backend Docs: http://localhost:8000/docs
#    - Flower: http://localhost:5555
#    - MinIO: http://localhost:9001
```

## Logs em Tempo Real

```powershell
# Todos os serviços
docker-compose -f docker-compose.prod.yml logs -f

# Apenas um serviço
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f celery_worker
docker-compose -f docker-compose.prod.yml logs -f postgres
```

## Troubleshooting

### ❌ "Port already in use"

```powershell
# Matar processo na porta
netstat -ano | findstr :5173      # Frontend
netstat -ano | findstr :8000      # Backend
# Depois: taskkill /PID <PID> /F
```

### ❌ Docker container não inicia

```powershell
# Ver logs detalhados
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs postgres

# Rebuildar imagens
docker-compose -f docker-compose.prod.yml build --no-cache
```

### ❌ PostgreSQL recusa conexão

```powershell
# Verificar se banco ficou saudável
docker-compose -f docker-compose.prod.yml ps
# Status deve ser "healthy" para postgres

# Limpar volumes e tentar novamente
docker volume rm learn_postgres_data
.\down.ps1 -Prune
.\up.ps1 -Detached
```

## Variáveis de Ambiente

- **Backend**: `.env.production` (configurações de produção-like)
- **Frontend**: `.env` (Vite carrega automático)

Para mudar comportamento: editar os arquivos `.env*` e rebuildar:

```powershell
docker-compose -f docker-compose.prod.yml build --no-cache
.\down.ps1
.\up.ps1 -Detached
```

## Desenvolvimento

Se não quer usar Docker:

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## CI/CD & Produção

Para deploy real em EasyPanel/Docker Swarm/Kubernetes, ver `docker-compose.prod.yml` e adaptar conforme sua infraestrutura.
