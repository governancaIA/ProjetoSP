# FiscalAI — Docker Compose Setup

## Visão Geral

Este guia descreve como executar a stack completa do FiscalAI usando Docker Compose.

**Stack incluído:**
- PostgreSQL 15 (banco de dados)
- Redis 7 (cache + task queue)
- MinIO (S3-compatible storage)
- FastAPI backend
- Celery worker
- Celery beat (scheduled tasks)
- Flower (Celery monitoring)
- React frontend (Vite)

---

## Pré-requisitos

1. **Docker & Docker Compose**
   ```powershell
   docker --version
   docker-compose --version
   ```

   Se não tiver instalado:
   - Windows: [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
   - Linux: `sudo apt-get install docker.io docker-compose`

2. **Git** (para clonar o repo)

---

## Primeiros Passos

### 1. Preparar Variáveis de Ambiente

```powershell
cd c:\Projetos\learn
copy .env.example .env
```

A maioria dos valores padrão funciona para desenvolvimento local.

### 2. Iniciar os Serviços

```powershell
docker-compose up --build
```

**O que vai acontecer:**
- Baixar imagens Docker
- Construir imagens do backend e frontend
- Iniciar todos os containers
- Criar tabelas no PostgreSQL
- Inicializar MinIO bucket

**Primeira execução:** Pode levar 5-10 minutos.

### 3. Verificar Status dos Serviços

Em outro terminal:

```powershell
docker-compose ps
```

Esperado:
```
NAME                    STATUS
fiscalai-postgres       Up (healthy)
fiscalai-redis          Up (healthy)
fiscalai-minio          Up (healthy)
fiscalai-backend        Up
fiscalai-celery-worker  Up
fiscalai-celery-beat    Up
fiscalai-flower         Up
fiscalai-frontend       Up
```

---

## Acessar os Serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | - |
| **Backend API** | http://localhost:8000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin_password_dev |
| **Flower (Celery)** | http://localhost:5555 | - |
| **PostgreSQL** | localhost:5432 | fiscalai_user / fiscalai_password_dev |
| **Redis** | localhost:6379 | - |

---

## Workflow de Desenvolvimento

### 1. Modificar Código (Backend)

```python
# backend/app/api/documents.py
# Faça suas mudanças...
```

O container do backend é iniciado com `--reload`, então as mudanças são detectadas automaticamente. Verifique os logs:

```powershell
docker-compose logs -f backend
```

### 2. Modificar Código (Frontend)

```tsx
// frontend/src/pages/DashboardPage.tsx
// Faça suas mudanças...
```

O Vite hot-reload atualiza automaticamente no browser.

```powershell
docker-compose logs -f frontend
```

### 3. Executar Testes

```powershell
# Testes do backend (dentro do container)
docker-compose exec backend pytest

# Testes com coverage
docker-compose exec backend pytest --cov=app

# Testes de integração
docker-compose exec backend pytest tests/integration/
```

### 4. Acessar Shell no Container

```powershell
# Backend Python shell
docker-compose exec backend bash

# Frontend Node shell
docker-compose exec frontend sh

# PostgreSQL psql
docker-compose exec postgres psql -U fiscalai_user -d fiscalai_db
```

---

## Verificações de Saúde

### Backend está respondendo?

```powershell
curl http://localhost:8000/health
# Esperado: {"status":"healthy","service":"FiscalAI API"}
```

### Banco de dados está pronto?

```powershell
docker-compose exec postgres pg_isready -U fiscalai_user -d fiscalai_db
# Esperado: accepting connections
```

### Redis está ativo?

```powershell
docker-compose exec redis redis-cli ping
# Esperado: PONG
```

### MinIO está funcional?

```powershell
docker-compose exec backend python -c "from minio import Minio; Minio('minio:9000', access_key='minioadmin', secret_key='minioadmin_password_dev'); print('? MinIO OK')"
```

---

## Troubleshooting

### "Port already in use"

Alguma porta está ocupada. Verifique:

```powershell
# Listar portas em uso
netstat -an | grep LISTENING

# Ou mude as portas no docker-compose.yml
# Exemplo: "5173:5173" ? "5174:5173"
```

### Backend não consegue conectar ao PostgreSQL

```powershell
# Verificar logs
docker-compose logs backend

# Garantir que postgres está saudável
docker-compose ps postgres

# Pode levar alguns segundos para estar pronto
docker-compose exec postgres pg_isready -U fiscalai_user
```

### Celery tasks não executam

```powershell
# Verificar worker
docker-compose logs celery-worker

# Verificar Redis
docker-compose exec redis redis-cli ping

# Monitorar em tempo real
docker-compose logs -f celery-worker
```

### Frontend não conecta ao backend

Verificar se `VITE_API_BASE_URL` está correto no `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Se estiver acessando via IP (ex: 192.168.x.x), ajuste para:

```env
VITE_API_BASE_URL=http://192.168.x.x:8000
```

### "Cannot find module"

Frontend dependencies não instaladas:

```powershell
docker-compose exec frontend npm ci
docker-compose restart frontend
```

---

## Limpeza

### Parar containers (sem remover dados)

```powershell
docker-compose stop
```

### Parar e remover containers

```powershell
docker-compose down
```

### Limpar tudo (volumes, imagens, containers)

```powershell
docker-compose down -v
# Isso remove também os volumes de dados (PostgreSQL, Redis, MinIO)
# Use com cuidado em produção!
```

### Reconstruir tudo do zero

```powershell
docker-compose down -v
docker-compose up --build
```

---

## Arquitetura dos Containers

```
+-----------------------------------------------------+
¦            Docker Network: fiscalai-network          ¦
+-----------------------------------------------------¦
¦                                                      ¦
¦  +--------------+      +------------------+        ¦
¦  ¦  Frontend    ¦      ¦   Backend API    ¦        ¦
¦  ¦ (React/Vite)¦?----?¦   (FastAPI)      ¦        ¦
¦  ¦ :5173        ¦ HTTP ¦ :8000            ¦        ¦
¦  +--------------+      +------------------+        ¦
¦                                 ¦                  ¦
¦         +-----------------------+-------------------+
¦         ¦                       ¦                   ¦
¦  +------?-----+      +----------?------+  +-------?------+
¦  ¦ PostgreSQL ¦      ¦    Redis        ¦  ¦   MinIO      ¦
¦  ¦ :5432      ¦      ¦ :6379           ¦  ¦ :9000/:9001  ¦
¦  +------------+      +-----------------+  +--------------+
¦                             ¦
¦         +-------------------+------------------+
¦         ¦                   ¦                  ¦
¦  +------?--------+  +------?-----+  +--------?--------+
¦  ¦ Celery Worker ¦  ¦ Celery Beat¦  ¦    Flower       ¦
¦  ¦ (async tasks) ¦  ¦(scheduled) ¦  ¦  (monitoring)   ¦
¦  +---------------+  +------------+  ¦ :5555           ¦
¦                                      +-----------------+
¦                                                      ¦
+-----------------------------------------------------+
```

---

## Próximos Passos

1. **Testar fluxo de login**
   - http://localhost:5173/login
   - Usar credenciais criadas via backend API

2. **Fazer upload de arquivos fiscais**
   - POST /api/v1/uploads/fiscal-documents
   - Enviar SPED + XML NF-e/CT-e

3. **Monitorar jobs Celery**
   - http://localhost:5555
   - Acompanhar processamento assíncrono

4. **Executar testes E2E**
   - Próxima fase após Docker Compose validado

---

## Entrar em Produção

Para deploy no VPS:

1. Substituir `MINIO_ENDPOINT` por S3 AWS
2. Substituir `POSTGRES_URL` por RDS
3. Adicionar SSL (nginx reverse proxy)
4. Configurar variáveis de segurança (SECRET_KEY, etc.)
5. Usar `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up`

Consulte [DEPLOYMENT.md](./DEPLOYMENT.md) para detalhes.
