# 📖 Guia Completo: Rodando FiscalAI no EasyPanel

> **Data:** 2026-05-25  
> **Status:** Passo-a-passo para deploy manual (recomendado)

---

## 🎯 O que é EasyPanel?

EasyPanel é uma plataforma de deploy que abstrai Docker. Você:
- Conecta seu GitHub
- Cria "Apps" apontando para Dockerfiles
- EasyPanel constrói e executa automaticamente
- Gerencia domínios e SSL grátis

**Seu FiscalAI já tem:** `docker-compose.prod.yml` pronto com Backend + Frontend + PostgreSQL + Redis + MinIO.

---

## ✅ Pré-requisitos

- [ ] Acesso ao EasyPanel (já tem: `6hjchk.easypanel.host`)
- [ ] Repositório GitHub com o código (público ou com deploy key)
- [ ] Branch `main` com o projeto sincronizado
- [ ] Senhas atualizadas (você tem `FiscalAI#Postgres2026!` e `FiscalAI#MinIO2026!@Secure`)

---

## 🚀 PASSO 1: Preparar o Repositório GitHub

### 1.1 Sincronize o código
```powershell
cd c:\Projetos\learn
git status
git add .
git commit -m "chore: prepare for EasyPanel deployment"
git push origin main
```

### 1.2 Verifique a estrutura
Certifique-se de que estes arquivos estão **commitados**:
- ✅ `backend/Dockerfile`
- ✅ `frontend/Dockerfile.prod`
- ✅ `infra/docker-compose.prod.yml`

---

## 🏗️ PASSO 2: Criar Apps no EasyPanel Dashboard

### 2.1 Backend App

1. Acesse: **https://dashboard.easypanel.io** → Dashboard → **Create new app**

2. Preencha:
   - **App Name:** `fiscalai-backend`
   - **Git Repo:** `https://github.com/seu/repo` (ou seu fork/clone)
   - **Branch:** `main`
   - **Dockerfile Path:** `./backend/Dockerfile`
   - **Build Command:** (deixe vazio ou padrão)
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`

3. Clique **Create** e aguarde o build (5-10 min)

4. Quando terminar, anote a URL gerada (ex: `chatwoot-fiscalai-backend.6hjchk.easypanel.host`)

---

### 2.2 Frontend App

1. **Create new app** novamente

2. Preencha:
   - **App Name:** `fiscalai-frontend`
   - **Git Repo:** mesmo repo
   - **Branch:** `main`
   - **Dockerfile Path:** `./frontend/Dockerfile.prod`
   - **Build Command:** (deixe vazio)
   - **Start Command:** (deixe vazio, use nginx padrão)

3. Clique **Create** e aguarde

4. Anote a URL (ex: `chatwoot-fiscalai-frontend.6hjchk.easypanel.host`)

---

### 2.3 PostgreSQL (Serviço Gerenciado)

1. No Dashboard → **Services** → **Add Service** → **PostgreSQL**

2. Configure:
   - **Name:** `fiscalai-postgres`
   - **Username:** `fiscalai_user`
   - **Password:** `FiscalAI#Postgres2026!` *(já configurado no docker-compose.prod.yml)*
   - **Database:** `fiscalai_db`

3. EasyPanel fornecerá a URL interna (ex: `postgres://...`)

4. **Copie essa URL** — você vai usar nas variáveis de ambiente

---

### 2.4 Redis (Serviço Gerenciado)

1. **Add Service** → **Redis**

2. Configure:
   - **Name:** `fiscalai-redis`
   - **Password:** (deixe em branco ou gere uma)

3. Copie a URL interna fornecida

---

### 2.5 MinIO (Serviço Gerenciado ou Docker)

Se EasyPanel **não** oferecer MinIO como serviço gerenciado:

**Opção A — Usar Docker (recomendado)**

1. **Create new app**
   - **App Name:** `fiscalai-minio`
   - **Git Repo:** mesmo repo
   - **Dockerfile Path:** (deixe vazio, use imagem padrão)
   - **Base Image:** `minio/minio:latest`
   - **Ports:** `9000` (API), `9001` (console)
   - **Environment Variables:** (ver seção abaixo)

**Opção B — Usar S3 AWS Real**

Se preferir não rodar MinIO:
- Use AWS S3 em vez de MinIO
- Altere `MINIO_*` para `AWS_*` nas variáveis de ambiente
- Atualize `app/services/storage_service.py` para usar boto3

---

## 🔐 PASSO 3: Configurar Variáveis de Ambiente

### 3.1 Para o Backend (`fiscalai-backend`)

Abra a app → **Settings** → **Environment Variables**

Adicione:

```env
# Database
DATABASE_URL=postgresql://fiscalai_user:FiscalAI#Postgres2026!@postgres-hostname:5432/fiscalai_db

# Redis
REDIS_URL=redis://redis-hostname:6379/0
CELERY_BROKER_URL=redis://redis-hostname:6379/1
CELERY_RESULT_BACKEND=redis://redis-hostname:6379/2

# MinIO / Object Storage
MINIO_ENDPOINT=minio-hostname:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=FiscalAI#MinIO2026!@Secure
MINIO_BUCKET=fiscalai-documents

# FastAPI Config
SECRET_KEY=k8xAmP9xvQ2rL5xnJ4wH7cF3bG6yT1Z
DEBUG=False
ENV=production
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host,http://localhost:5173

# Allowed Hosts
ALLOWED_HOSTS=chatwoot-fiscalai-backend.6hjchk.easypanel.host,backend,localhost,127.0.0.1
```

**⚠️ IMPORTANTE:** Substitua `postgres-hostname`, `redis-hostname`, `minio-hostname` pelos valores **reais** fornecidos pelo EasyPanel após criar os serviços.

---

### 3.2 Para o Frontend (`fiscalai-frontend`)

Abra a app → **Settings** → **Environment Variables**

Adicione:

```env
VITE_API_BASE_URL=https://chatwoot-fiscalai-backend.6hjchk.easypanel.host
NODE_ENV=production
```

---

### 3.3 Para MinIO (se rodar como Docker App)

Adicione:

```env
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=FiscalAI#MinIO2026!@Secure
MINIO_BROWSER_REDIRECT_URL=https://console-chatwoot-minio.6hjchk.easypanel.host
```

---

## 🔗 PASSO 4: Configurar Domínios e SSL

### 4.1 Domínios Customizados (Opcional)

Se quiser apontá-los para seu domínio (ex: `fiscalai.seudominio.com.br`):

1. Acesse **Domains** no Dashboard EasyPanel
2. Adicione: `fiscalai.seudominio.com.br` → aponte para `fiscalai-frontend`
3. Adicione: `api.fiscalai.seudominio.com.br` → aponte para `fiscalai-backend`
4. EasyPanel gera SSL automaticamente (Let's Encrypt)

Aguarde ~5 min para DNS propagar.

---

### 4.2 Usar Domínios Default (Mais Rápido)

Se não quiser domínio customizado, os URLs default funcionam:
- Frontend: `https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host`
- Backend: `https://chatwoot-fiscalai-backend.6hjchk.easypanel.host`

SSL já vem configurado grátis.

---

## 🧪 PASSO 5: Testar a Stack

### 5.1 Health Checks

Teste os endpoints:

```powershell
# Backend
curl https://chatwoot-fiscalai-backend.6hjchk.easypanel.host/health
# Espera: {"status": "ok"}

# Frontend (abre no browser)
https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host
# Espera: página de login do FiscalAI
```

### 5.2 Verificar Banco de Dados

Conecte-se ao PostgreSQL (usando credenciais fornecidas):

```powershell
# Usando psql (se instalado)
psql "postgresql://fiscalai_user:FiscalAI#Postgres2026!@postgres-hostname:5432/fiscalai_db"

# Ou use DBeaver com a connection string
```

### 5.3 Verificar MinIO

Acesse a console:
```
https://console-chatwoot-minio.6hjchk.easypanel.host
User: minioadmin
Password: FiscalAI#MinIO2026!@Secure
```

---

## 🔧 Troubleshooting

### Problema: "Connection refused" ao Backend

**Causa:** As variáveis de ambiente estão com hostnames incorretos.

**Solução:**
1. No Dashboard EasyPanel, clique na app `fiscalai-backend` → **Logs**
2. Procure por erros de conexão (DATABASE_URL, REDIS_URL, etc.)
3. Corrija os hostnames nas variáveis de ambiente

---

### Problema: Frontend não carrega / API retorna 404

**Causa:** `VITE_API_BASE_URL` incorreta ou CORS não configurado.

**Solução:**
1. Abra Dev Tools (F12) → **Console** e veja os erros de rede
2. Confirme que `VITE_API_BASE_URL` aponta para o backend correto
3. Verifique `CORS_ORIGINS` no backend inclui a URL do frontend

---

### Problema: Arquivo não é salvo no MinIO

**Causa:** MinIO não está acessível ou credenciais incorretas.

**Solução:**
1. Teste acesso direto à console MinIO
2. Verifique bucket `fiscalai-documents` existe
3. Confirme `MINIO_*` environment variables no backend

---

## 🔄 Celery Workers (Processamento Assíncrono)

O FiscalAI usa Celery para processar uploads em background.

Se quiser rodá-lo:

1. **Create new app** → `fiscalai-celery-worker`
2. **Dockerfile Path:** `./backend/Dockerfile`
3. **Start Command:** `celery -A app.core.celery_app worker --loglevel=info --concurrency=4`
4. **Environment Variables:** (mesmo do backend)

Monitorar tarefas:
```
1. Create app → `fiscalai-flower`
2. Base Image: `minio/minio:latest` (ou reutilize o Dockerfile)
3. Start Command: `celery -A app.core.celery_app flower --port=5555`
4. Port: 5555
```

---

## 🔐 Segurança em Produção

Antes de deixar o app live:

- [ ] Altere `SECRET_KEY` em `PASSO 3`
- [ ] Use senhas fortes para PostgreSQL, Redis, MinIO
- [ ] Habilite SSL/TLS (EasyPanel faz automático)
- [ ] Configure backup automático do banco (EasyPanel oferece)
- [ ] Revise `CORS_ORIGINS` — só incluir domínios confiáveis
- [ ] Configure logs centralizados (Sentry, Datadog, etc.)
- [ ] Habilite WAF se disponível

---

## 📊 Próximos Passos

Após deploy bem-sucedido:

1. **Migrações de Banco:** Rode `alembic upgrade head` no backend
2. **Criar usuário admin:** Use endpoint POST `/api/auth/register` ou admin CLI
3. **Upload de teste:** Suba um arquivo SPED para validar pipeline
4. **Monitorar logs:** Dashboard → Apps → Logs (procure por erros)

---

## 📝 Checklist Final

- [ ] Código synced no GitHub (main branch)
- [ ] 2 apps criados (Backend + Frontend) no EasyPanel
- [ ] Serviços PostgreSQL, Redis (+ MinIO se necessário) criados
- [ ] Variáveis de ambiente configuradas em ambos os apps
- [ ] Domínios configurados (padrão ou customizado)
- [ ] SSL ativo e funcionando
- [ ] Backend responde com `/health`
- [ ] Frontend carrega e conecta ao backend
- [ ] Teste um upload de documento
- [ ] Logs limpos (sem erros críticos)

---

## ❓ Dúvidas?

Procure no EasyPanel:
- **Docs:** https://easypanel.io/docs
- **Community:** Discord do EasyPanel
- **Status:** https://status.easypanel.io

