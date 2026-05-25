# ⚡ Quick Start — FiscalAI no EasyPanel

**TL;DR:** 5 passos para rodar seu app.

---

## 1️⃣ Sincronizar GitHub
```powershell
cd c:\Projetos\learn
git push origin main
```

---

## 2️⃣ Criar 2 Apps no Dashboard (https://dashboard.easypanel.io)

### Backend
| Campo | Valor |
|---|---|
| **App Name** | `fiscalai-backend` |
| **Dockerfile Path** | `./backend/Dockerfile` |
| **Port** | 8000 |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |

### Frontend
| Campo | Valor |
|---|---|
| **App Name** | `fiscalai-frontend` |
| **Dockerfile Path** | `./frontend/Dockerfile.prod` |
| **Port** | 80 |

---

## 3️⃣ Criar Serviços (PostgreSQL, Redis, MinIO)

No Dashboard → **Services**:

| Serviço | User | Password | Database |
|---|---|---|---|
| **PostgreSQL** | `fiscalai_user` | `FiscalAI#Postgres2026!` | `fiscalai_db` |
| **Redis** | - | (deixe vazio) | - |
| **MinIO** | `minioadmin` | `FiscalAI#MinIO2026!@Secure` | - |

**Copie as URLs internas fornecidas pelo EasyPanel.**

---

## 4️⃣ Configurar Variáveis de Ambiente

### Backend App → Settings → Environment Variables

```env
DATABASE_URL=postgresql://fiscalai_user:FiscalAI#Postgres2026!@POSTGRES_HOSTNAME:5432/fiscalai_db
REDIS_URL=redis://REDIS_HOSTNAME:6379/0
CELERY_BROKER_URL=redis://REDIS_HOSTNAME:6379/1
CELERY_RESULT_BACKEND=redis://REDIS_HOSTNAME:6379/2
MINIO_ENDPOINT=MINIO_HOSTNAME:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=FiscalAI#MinIO2026!@Secure
MINIO_BUCKET=fiscalai-documents
SECRET_KEY=k8xAmP9xvQ2rL5xnJ4wH7cF3bG6yT1Z
DEBUG=False
ENV=production
CORS_ORIGINS=https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host
ALLOWED_HOSTS=chatwoot-fiscalai-backend.6hjchk.easypanel.host,backend,localhost,127.0.0.1
```

**⚠️ Substitua `POSTGRES_HOSTNAME`, `REDIS_HOSTNAME`, `MINIO_HOSTNAME` pelos valores reais.**

### Frontend App → Settings → Environment Variables

```env
VITE_API_BASE_URL=https://chatwoot-fiscalai-backend.6hjchk.easypanel.host
NODE_ENV=production
```

---

## 5️⃣ Validar

Aguarde os builds terminarem (5-10 min).

Teste:
```powershell
# Backend
curl https://chatwoot-fiscalai-backend.6hjchk.easypanel.host/health

# Frontend (browser)
https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host
```

✅ Pronto! Seu FiscalAI está no ar.

---

## 🐛 Deu erro?

1. **Backend não conecta ao banco:** Verifique `DATABASE_URL` nas env vars
2. **Frontend não carrega:** Verifique `VITE_API_BASE_URL`
3. **Arquivo não salva:** Verifique MinIO está rodando

Veja logs em: Dashboard → App → **Logs**

---

## 📖 Guia Completo

Para detalhes, veja: [`EASYPANEL_SETUP_GUIA.md`](EASYPANEL_SETUP_GUIA.md)
