# 🏗️ Arquitetura FiscalAI no EasyPanel

## Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERNET (HTTPS/SSL)                     │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
    ┌────────▼─────────┐          ┌──────────▼──────────┐
    │  Frontend React  │          │  Backend FastAPI   │
    │  (Port 80/443)   │          │  (Port 8000)       │
    │  EasyPanel App   │          │  EasyPanel App     │
    └────────┬─────────┘          └──────────┬─────────┘
             │                              │
             │ CORS Request                │ API Response
             │ (VITE_API_BASE_URL)         │
             └──────────┬───────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼──────┐   ┌────▼──────┐  ┌────▼──────┐
   │PostgreSQL │   │   Redis   │  │  MinIO   │
   │ Database  │   │  Cache &  │  │ S3 Files │
   │           │   │  Broker   │  │          │
   └───────────┘   └───────────┘  └──────────┘
   (Managed)       (Managed)      (App Docker)
```

---

## Componentes

### 1. **Frontend (React + Vite)**

**O quê:**
- Interface de usuário do FiscalAI
- Upload de arquivos
- Dashboard com gráficos
- Relatórios

**Onde roda:**
- EasyPanel App: `fiscalai-frontend`
- Dockerfile: `frontend/Dockerfile.prod`
- Porta: `80` (HTTP) → `443` (HTTPS/SSL automático)
- Build: Vite (compile para static files) + Nginx (serve)

**Como se conecta ao Backend:**
```
Frontend (React)
  ↓ (AJAX/Fetch)
VITE_API_BASE_URL = "https://chatwoot-fiscalai-backend.6hjchk.easypanel.host"
  ↓
Backend (FastAPI)
```

---

### 2. **Backend (FastAPI)**

**O quê:**
- API REST para upload, validação, scoring
- Executa regras fiscais
- Gerencia banco de dados
- Integra com Redis e MinIO

**Onde roda:**
- EasyPanel App: `fiscalai-backend`
- Dockerfile: `backend/Dockerfile`
- Porta: `8000` → URL: `https://chatwoot-fiscalai-backend.6hjchk.easypanel.host`

**Dependências:**
- PostgreSQL (banco de dados)
- Redis (cache + broker Celery)
- MinIO (armazenamento de arquivos)

**Variáveis críticas:**
```env
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
MINIO_ENDPOINT=minio:9000
```

---

### 3. **PostgreSQL (Banco de Dados)**

**O quê:**
- Armazena usuários, documentos, logs de validação
- Multi-tenant (um schema por cliente)
- Migrations com Alembic

**Onde roda:**
- EasyPanel Managed Service (gerenciado pelo EasyPanel)
- Porta: `5432` (interna)
- Credenciais:
  - User: `fiscalai_user`
  - Password: `FiscalAI#Postgres2026!`
  - Database: `fiscalai_db`

**Acesso:**
- De dentro do container backend: `postgresql://fiscalai_user:FiscalAI#Postgres2026!@postgres-service:5432/fiscalai_db`
- De fora (seu PC): usar tunnel ou proxy

---

### 4. **Redis (Cache & Task Broker)**

**O quê:**
- Cache de sessão, dados fiscais
- Message broker para Celery (fila de tarefas)
- Gerencia locks distribuídos

**Onde roda:**
- EasyPanel Managed Service
- Porta: `6379` (interna)

**Uso no Backend:**
```python
# Cache
redis://redis-service:6379/0

# Celery Broker
redis://redis-service:6379/1

# Celery Result Backend
redis://redis-service:6379/2
```

---

### 5. **MinIO (Armazenamento S3-Compatível)**

**O quê:**
- Armazena SPED, XML NF-e, CT-e em buckets
- Console web para gerenciamento
- API S3-compatível

**Onde roda:**
- EasyPanel Docker App: `fiscalai-minio`
- Porta: `9000` (API S3) + `9001` (console web)
- Credenciais:
  - User: `minioadmin`
  - Password: `FiscalAI#MinIO2026!@Secure`

**Acesso:**
- S3 API: `http://minio:9000` (de dentro)
- Console: `https://console-chatwoot-minio.6hjchk.easypanel.host` (de fora)

---

## Fluxo de Upload de Documento

```
1. Usuário abre Frontend
   ↓
2. Clica "Upload SPED.txt"
   ↓
3. Frontend faz POST para Backend
   POST /api/uploads/
   Content-Type: multipart/form-data
   ↓
4. Backend recebe, salva em MinIO
   s3://fiscalai-documents/tenant-123/sped-2024-jan.txt
   ↓
5. Backend fila Celery task: "parse_document"
   ↓
6. Celery Worker pega task do Redis
   ↓
7. Worker parse SPED, executa validações
   ↓
8. Worker salva resultado no PostgreSQL
   ↓
9. Frontend pooling: GET /api/documents/{id}/status
   ↓
10. Frontend exibe resultados em tempo real
```

---

## Variáveis de Ambiente

### Frontend

| Var | Valor | Tipo |
|---|---|---|
| `VITE_API_BASE_URL` | `https://chatwoot-fiscalai-backend.6hjchk.easypanel.host` | URL completa |
| `NODE_ENV` | `production` | String |

---

### Backend

| Var | Valor | Tipo |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | Connection String |
| `REDIS_URL` | `redis://...` | Connection String |
| `CELERY_BROKER_URL` | `redis://...:6379/1` | Connection String |
| `CELERY_RESULT_BACKEND` | `redis://...:6379/2` | Connection String |
| `MINIO_ENDPOINT` | `minio:9000` | Host:Port |
| `MINIO_ROOT_USER` | `minioadmin` | String |
| `MINIO_ROOT_PASSWORD` | `FiscalAI#MinIO2026!@Secure` | String |
| `MINIO_BUCKET` | `fiscalai-documents` | Bucket name |
| `SECRET_KEY` | `k8xAmP9...` | Random string |
| `DEBUG` | `False` | Boolean |
| `ENV` | `production` | String |
| `CORS_ORIGINS` | `https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host` | URL |
| `ALLOWED_HOSTS` | `chatwoot-fiscalai-backend.6hjchk.easypanel.host,backend` | Comma-separated |

---

## Healthchecks

EasyPanel monitora automaticamente:

### Frontend
```
GET https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host/
→ HTTP 200 + HTML
```

### Backend
```
GET https://chatwoot-fiscalai-backend.6hjchk.easypanel.host/health
→ HTTP 200 + {"status": "ok"}
```

### PostgreSQL
```
psql -U fiscalai_user -d fiscalai_db -c "SELECT 1"
```

### Redis
```
redis-cli ping
→ PONG
```

### MinIO
```
curl http://minio:9000/minio/health/live
→ HTTP 200
```

---

## Logs

Cada app tem logs em tempo real no EasyPanel Dashboard.

**Acesso:**
- Dashboard → App → **Logs**

**Locais importantes a monitorar:**

- **Backend errors:** `ERROR: DatabaseError` (connection string incorreta)
- **Frontend errors:** `Module not found` (build falhou)
- **MinIO errors:** `Cannot connect to minio` (credenciais)

---

## Scaling (Fase 2)

Atualmente tudo roda em 1 container por serviço.

Para escalar:

| Componente | Estratégia |
|---|---|
| **Frontend** | Multi-região CDN (CloudFlare, Akamai) |
| **Backend** | Múltiplas replicas + load balancer |
| **PostgreSQL** | Read replicas ou managed DB (AWS RDS) |
| **Redis** | Cluster ou Managed (AWS ElastiCache) |
| **MinIO** | S3 AWS real ou MinIO distribuído |
| **Celery** | Múltiplos workers + auto-scaling |

---

## Custos (Estimativa)

**No EasyPanel:**
- Frontend App: $5-15/mês (conforme traffic)
- Backend App: $10-30/mês
- PostgreSQL: $10-50/mês (managed)
- Redis: $5-20/mês (managed)
- MinIO: $0 (parte da app) ou $5-20/mês se managed

**Total:** ~$30-150/mês para MVP

**Alternativa — AWS/GCP:**
- Mais caro (~$100-300/mês inicial)
- Mais controle e escalabilidade
- Terraform pronto para migrar (ver `infra/terraform/`)

---

## Troubleshooting Arquitetura

### "Connection refused" — Database

**Sintoma:** Backend logs show `ERROR: Cannot connect to postgresql://...`

**Causa:** `DATABASE_URL` tem hostname incorreto

**Fix:**
1. Dashboard → `fiscalai-backend` → Settings → Environment
2. Procure pela URL do PostgreSQL que EasyPanel gerou
3. Verifique: hostname, porta, user, password, database

---

### "CORS error" — Frontend não fala com Backend

**Sintoma:** Browser console: `Access-Control-Allow-Origin: https://... is not allowed`

**Causa:** `CORS_ORIGINS` no backend não inclui o frontend

**Fix:**
```env
CORS_ORIGINS=https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host,http://localhost:5173
```

---

### "Arquivo não aparece" — MinIO indisponível

**Sintoma:** Upload funciona mas arquivo sumiu

**Causa:** MinIO credenciais incorretas ou bucket não existe

**Fix:**
1. Acesse console: `https://console-chatwoot-minio.6hjchk.easypanel.host`
2. Login: `minioadmin` / `FiscalAI#MinIO2026!@Secure`
3. Verifique se bucket `fiscalai-documents` existe
4. Se não, crie manualmente ou deixe backend criar

---

## Próximas Fases

### Fase 2 (3 meses)
- [ ] Múltiplas replicas do backend (load balancing)
- [ ] Database replication (HA)
- [ ] Monitoring com Prometheus + Grafana
- [ ] Alertas em Slack

### Fase 3 (6 meses)
- [ ] Migrar para AWS/GCP com Terraform
- [ ] S3 em vez de MinIO
- [ ] RDS em vez de PostgreSQL self-managed
- [ ] ElastiCache em vez de Redis self-managed

