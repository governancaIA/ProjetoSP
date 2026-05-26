# 🚀 FiscalAI — Deploy Completo (Local + EasyPanel)

## 📍 Dois Cenários

### 1️⃣ **Local (Desenvolvimento/Teste Rápido)**
### 2️⃣ **EasyPanel (Produção)**

---

## 🏠 CENÁRIO 1: Rodar Localmente (Docker Compose)

### Pré-requisitos
- Docker Desktop instalado
- PowerShell 5.0+
- 4+ GB RAM disponível

### Um Comando Para Tudo

```powershell
cd c:\Projetos\learn
.\up.ps1 -Detached           # Levanta stack em background
Start-Sleep -Seconds 30       # Aguarda containers ficarem saudáveis
.\init-db.ps1                 # Inicializa banco de dados
```

### Acessar

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | — |
| **Backend API** | http://localhost:8000/docs | — |
| **Flower** (Celery UI) | http://localhost:5555 | — |
| **MinIO** | http://localhost:9001 | minioadmin / minioadmin_password |
| **PostgreSQL** | localhost:5432 | fiscalai_user / fiscalai_password |

### Parar

```powershell
.\down.ps1                    # Para containers
# ou
.\down.ps1 -Prune            # Para + limpa tudo
```

---

## 🌐 CENÁRIO 2: Deploy no EasyPanel (Produção)

### Visão Geral

EasyPanel é um PaaS que:
- Conecta ao GitHub
- Faz build automático de Dockerfiles
- Gerencia domínios + SSL grátis
- Monitora logs e saúde dos apps

**Seu setup:**
- Backend FastAPI (Dockerfile)
- Frontend React (Dockerfile.prod)
- PostgreSQL (serviço gerenciado)
- Redis (serviço gerenciado)
- MinIO (Docker app)

### 🔑 Checklist Deploy (30-40 min)

#### ✅ PASSO 1: GitHub Sync (2 min)

```powershell
cd c:\Projetos\learn
git push origin main
```

- [ ] Push sucedido
- [ ] Branch `main` atualizado no GitHub

---

#### ✅ PASSO 2: Criar Apps no Dashboard (15 min)

Acesse: https://dashboard.easypanel.io

**Backend App**
1. **Create new app**
   - Name: `fiscalai-backend`
   - Repo: `seu-repo-github` (branch: `main`)
   - Dockerfile Path: `./backend/Dockerfile`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Clique **Create** e aguarde build (5-7 min)
3. **Anote URL:** `https://chatwoot-fiscalai-backend.6hjchk.easypanel.host` ← substitua `chatwoot` pelo seu prefixo

**Frontend App**
1. **Create new app**
   - Name: `fiscalai-frontend`
   - Repo: mesmo
   - Dockerfile Path: `./frontend/Dockerfile.prod`
2. Clique **Create** e aguarde (3-5 min)
3. **Anote URL:** `https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host`

- [ ] Backend build completo
- [ ] Frontend build completo
- [ ] URLs anotadas

---

#### ✅ PASSO 3: Criar Serviços (10 min)

Dashboard → **Services** → **Add Service**

**PostgreSQL**
- Name: `fiscalai-postgres`
- Username: `fiscalai_user`
- Password: `FiscalAI#Postgres2026!`
- Database: `fiscalai_db`
- **Copie URL interna fornecida** (ex: `postgres.local:5432`)

**Redis**
- Name: `fiscalai-redis`
- Password: (deixe vazio)
- **Copie URL interna** (ex: `redis.local:6379`)

**MinIO** (opção: Docker App ou Managed)
- Name: `fiscalai-minio`
- Access Key: `minioadmin`
- Secret Key: `FiscalAI#MinIO2026!@Secure`
- **Copie URL interna** (ex: `minio.local:9000`)

- [ ] PostgreSQL criado
- [ ] Redis criado
- [ ] MinIO criado
- [ ] Hostnames anotados

---

#### ✅ PASSO 4: Variáveis de Ambiente (5 min)

**Backend App** → Settings → Environment Variables

Cole:
```env
DATABASE_URL=postgresql://fiscalai_user:FiscalAI#Postgres2026!@[POSTGRES_HOSTNAME]:5432/fiscalai_db
REDIS_URL=redis://[REDIS_HOSTNAME]:6379/0
CELERY_BROKER_URL=redis://[REDIS_HOSTNAME]:6379/1
CELERY_RESULT_BACKEND=redis://[REDIS_HOSTNAME]:6379/2
MINIO_ENDPOINT=[MINIO_HOSTNAME]:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=FiscalAI#MinIO2026!@Secure
MINIO_BUCKET=fiscalai-documents
SECRET_KEY=k8xAmP9xvQ2rL5xnJ4wH7cF3bG6yT1Z
DEBUG=False
ENV=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host,http://localhost:5173
ALLOWED_HOSTS=chatwoot-fiscalai-backend.6hjchk.easypanel.host,backend,localhost
```

**Substitua os bracketes pelos values anotados:**
- `[POSTGRES_HOSTNAME]` → hostname do PostgreSQL
- `[REDIS_HOSTNAME]` → hostname do Redis
- `[MINIO_HOSTNAME]` → hostname do MinIO

**Frontend App** → Settings → Environment Variables

Cole:
```env
VITE_API_BASE_URL=https://chatwoot-fiscalai-backend.6hjchk.easypanel.host
NODE_ENV=production
```

- [ ] Backend env vars salvas
- [ ] Frontend env vars salvas
- [ ] Apps reiniciaram

---

#### ✅ PASSO 5: Testar (5 min)

**Terminal:**
```powershell
# Backend health check
curl https://chatwoot-fiscalai-backend.6hjchk.easypanel.host/health
# Esperado: {"status": "ok"}
```

**Browser:**
```
https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host
# Esperado: Página de login carrega
```

**DevTools (F12):**
1. Abra console
2. Faça qualquer ação que chame API
3. Procure por erros de CORS

- [ ] Backend responde
- [ ] Frontend carrega
- [ ] Sem erros de CORS

---

### 🎯 Pronto Para Produção!

Se passou em todos os testes:

```powershell
# Sincronize os changes mais recentes
git push origin main

# Redeploy (manual ou automático)
# Dashboard → Backend App → Redeploy
```

---

## 🐛 Troubleshooting

| Erro | Solução |
|------|---------|
| **Backend 502** | DATABASE_URL incorreta. Verifique hostname do PostgreSQL no dashboard |
| **Frontend 404** | VITE_API_BASE_URL errada. Confirme URL do backend |
| **CORS error na console** | CORS_ORIGINS no backend não inclui frontend URL |
| **File upload falha** | MinIO não está rodando. Verifique MINIO_ENDPOINT |
| **App não inicia** | Ver logs: Dashboard → App → **Logs** → procure ERROR |

**Para ver logs detalhados:**
```
Dashboard → App → Logs (vê últimas 100 linhas)
```

---

## 📊 Monitorar em Produção

### Logs
```
Dashboard → App → Logs (real-time)
Procure: ERROR, WARNING, timeout, connection refused
```

### Health Checks
```powershell
# A cada 5 min
for ($i=0; $i -lt 10; $i++) {
  curl https://chatwoot-fiscalai-backend.6hjchk.easypanel.host/health
  Start-Sleep -Seconds 300  # 5 min
}
```

### MinIO Console
```
https://console-chatwoot-minio.6hjchk.easypanel.host
User: minioadmin
Pass: FiscalAI#MinIO2026!@Secure
```

---

## 🔄 Fluxo de Deploy Iterativo

Após primeira subida:

```powershell
# 1. Code change local
# 2. Commit e push
git add .
git commit -m "fix: algo"
git push origin main

# 3. EasyPanel reconstrói automaticamente (se configured)
# Ou manualmente:
# Dashboard → Backend → Build → Redeploy

# 4. Monitorar logs
# Dashboard → Logs → procure por erro

# 5. If issue, fix local + retry
```

---

## 📚 Referências

- **EasyPanel Docs:** https://easypanel.io/docs
- **Docker Compose Local:** Ver `QUICKSTART.md`
- **Setup Completo:** Ver `infra/EASYPANEL_SETUP_GUIA.md`
- **Checklist Detalhado:** Ver `infra/CHECKLIST_DEPLOY.md`
