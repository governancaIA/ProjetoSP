# ✅ Checklist Deploy FiscalAI no EasyPanel

**Tempo estimado:** 30-40 min  
**Data:** 2026-05-25  
**Status:** Siga passo-a-passo

---

## 📋 PRÉ-DEPLOY (5 min)

- [ ] Abrir navegador em https://dashboard.easypanel.io
- [ ] Verificar que está logado (canto superior direito)
- [ ] Verificar acesso ao repositório GitHub (público ou deploy key configurada)
- [ ] Terminal aberto em `c:\Projetos\learn`

---

## 🔄 SINCRONIZAR GITHUB (2 min)

```powershell
cd c:\Projetos\learn
git status
# Verificar se há uncommitted changes
git add .
git commit -m "chore: prepare EasyPanel deployment"
git push origin main
```

- [ ] `git push` sucedido (sem erros)
- [ ] Branch `main` sincronizado no GitHub

---

## 🏗️ CRIAR APPS NO EASYPANEL (15 min)

### BACKEND APP

No Dashboard → **Create new app**

Preencher:
- [ ] **App Name:** `fiscalai-backend`
- [ ] **Git Repo:** (copiar seu repo URL)
- [ ] **Branch:** `main`
- [ ] **Dockerfile Path:** `./backend/Dockerfile`
- [ ] **Build Command:** (deixar vazio)
- [ ] **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`

Clicar: **Create**

Aguardar build (5-7 min):
- [ ] Build iniciado (vê "Building..." no log)
- [ ] Build finalizado (vê container running)
- [ ] **Anotar URL:** `https://chatwoot-fiscalai-backend.6hjchk.easypanel.host`

---

### FRONTEND APP

No Dashboard → **Create new app**

Preencher:
- [ ] **App Name:** `fiscalai-frontend`
- [ ] **Git Repo:** (mesmo repo)
- [ ] **Branch:** `main`
- [ ] **Dockerfile Path:** `./frontend/Dockerfile.prod`
- [ ] **Build Command:** (deixar vazio)

Clicar: **Create**

Aguardar build (3-5 min):
- [ ] Build iniciado
- [ ] Build finalizado
- [ ] **Anotar URL:** `https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host`

---

## 🗄️ CRIAR SERVIÇOS (10 min)

### POSTGRESQL

Dashboard → **Services** → **Add Service** → **PostgreSQL**

Preencher:
- [ ] **Name:** `fiscalai-postgres`
- [ ] **Username:** `fiscalai_user`
- [ ] **Password:** `FiscalAI#Postgres2026!`
- [ ] **Database:** `fiscalai_db`
- [ ] **Port:** `5432` (padrão)

Clicar: **Create**

Aguardar:
- [ ] Serviço criado
- [ ] **Copiar URL interna:** `postgresql://fiscalai_user:FiscalAI#Postgres2026!@HOSTNAME:5432/fiscalai_db`
- [ ] **Anotar HOSTNAME:** `_________` (substitua na URL acima)

---

### REDIS

Dashboard → **Services** → **Add Service** → **Redis**

Preencher:
- [ ] **Name:** `fiscalai-redis`
- [ ] **Port:** `6379` (padrão)
- [ ] **Password:** (deixar vazio ou gerar)

Clicar: **Create**

Aguardar:
- [ ] Serviço criado
- [ ] **Copiar URL interna:** `redis://HOSTNAME:6379`
- [ ] **Anotar HOSTNAME:** `_________`

---

### MINIO (Opção A: Docker App)

Se EasyPanel não oferece MinIO como serviço gerenciado:

Dashboard → **Create new app**

Preencher:
- [ ] **App Name:** `fiscalai-minio`
- [ ] **Base Image:** `minio/minio:latest`
- [ ] **Ports:** `9000`, `9001`
- [ ] **Start Command:** `minio server /data --console-address ":9001"`

Variáveis de Ambiente:
```env
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=FiscalAI#MinIO2026!@Secure
```

- [ ] App criado
- [ ] **Anotar HOSTNAME:** `_________`

---

### MINIO (Opção B: Managed Service)

Se EasyPanel oferece MinIO como serviço:

Dashboard → **Services** → **Add Service** → **MinIO**

- [ ] **Name:** `fiscalai-minio`
- [ ] **Access Key:** `minioadmin`
- [ ] **Secret Key:** `FiscalAI#MinIO2026!@Secure`

- [ ] Serviço criado
- [ ] **Copiar URL S3:** `s3://HOSTNAME:9000`
- [ ] **Anotar HOSTNAME:** `_________`

---

## ⚙️ CONFIGURAR VARIÁVEIS DE AMBIENTE (5 min)

### Para `fiscalai-backend`

Dashboard → `fiscalai-backend` → **Settings** → **Environment Variables**

Clique **Add Variable** e preencha cada linha:

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
ALLOWED_HOSTS=chatwoot-fiscalai-backend.6hjchk.easypanel.host,backend,localhost,127.0.0.1
```

- [ ] Todas as variáveis adicionadas
- [ ] Substitua `[POSTGRES_HOSTNAME]`, `[REDIS_HOSTNAME]`, `[MINIO_HOSTNAME]` pelos valores anotados acima
- [ ] Clique **Save**
- [ ] App reinicia automaticamente (aguarde 2-3 min)

---

### Para `fiscalai-frontend`

Dashboard → `fiscalai-frontend` → **Settings** → **Environment Variables**

```env
VITE_API_BASE_URL=https://chatwoot-fiscalai-backend.6hjchk.easypanel.host
NODE_ENV=production
```

- [ ] Variáveis adicionadas
- [ ] Clique **Save**
- [ ] App reinicia (aguarde 2-3 min)

---

## 🧪 VALIDAR DEPLOYMENT (5 min)

### Teste Backend

No terminal ou browser:
```powershell
curl https://chatwoot-fiscalai-backend.6hjchk.easypanel.host/health
```

Esperado:
```json
{"status": "ok"}
```

- [ ] Backend responde com HTTP 200

---

### Teste Frontend

No browser:
```
https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host
```

Esperado: Página de login do FiscalAI carrega normalmente

- [ ] Frontend carrega sem erros
- [ ] Pode ver logo, formulário de login, etc.

---

### Teste Conexão

No Frontend:
1. Abra DevTools (F12)
2. Aba **Console**
3. Faça qualquer ação que chame API (ex: clicar em botão)
4. Veja se há erros de CORS ou conexão

Esperado: Nenhum erro de CORS

- [ ] Nenhum erro de CORS na console

---

### Teste MinIO (Opcional)

No browser:
```
https://console-chatwoot-minio.6hjchk.easypanel.host
```

Login:
- User: `minioadmin`
- Password: `FiscalAI#MinIO2026!@Secure`

- [ ] MinIO console abre
- [ ] Consegue ver buckets
- [ ] Bucket `fiscalai-documents` existe (crie se não existir)

---

## 📊 MONITORAR LOGS (Contínuo)

Dashboard → App → **Logs**

Procure por erros:
- [ ] `ERROR: Cannot connect to postgresql://...` → DATABASE_URL incorreta
- [ ] `ERROR: Cannot connect to redis://...` → REDIS_URL incorreta
- [ ] `ERROR: Connection refused` → Serviço não está rodando
- [ ] `ModuleNotFoundError` → Falta dependência no Dockerfile

**Se houver erros:**
1. Leia a mensagem
2. Corrija a variável de ambiente
3. Salve
4. App reinicia automaticamente

- [ ] Logs do backend parecem saudáveis (sem ERROR)
- [ ] Logs do frontend parecem saudáveis

---

## 🎉 PRONTO!

Se chegou aqui:
- [ ] Backend está rodando
- [ ] Frontend está rodando
- [ ] Consegue fazer login (ou ver tela de login)
- [ ] Pode fazer upload de arquivo (teste com um SPED small)
- [ ] Arquivo aparece na dashboard

---

## 🐛 Deu erro? (Troubleshooting)

| Sintoma | Causa Comum | Solução |
|---|---|---|
| Backend 502 Bad Gateway | Database URL incorreta | Verificar `DATABASE_URL` |
| Frontend 404 / CORS error | Hostname errado | Verificar `VITE_API_BASE_URL` |
| Arquivo não salva | MinIO off | Verificar `MINIO_*` variables |
| App não inicia | Falta variável obrigatória | Comparar com lista acima |
| Build falha | Arquivo Dockerfile corrupto | Verificar Dockerfile localmente |

**Se não resolver:**
1. Veja logs completos (Dashboard → Logs)
2. Copie erro completo
3. Procure em Google: `"erro exato" easypanel` ou `"erro exato" docker`

---

## 📝 Anotar Hostnames (Referência)

Preencha aqui para referência rápida:

```
PostgreSQL Hostname: ___________________________________
Redis Hostname:      ___________________________________
MinIO Hostname:      ___________________________________

Backend URL: https://chatwoot-fiscalai-backend.6hjchk.easypanel.host
Frontend URL: https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host
MinIO Console: https://console-chatwoot-minio.6hjchk.easypanel.host
```

---

## ✅ Assinado

- Data de conclusão: _______________
- Quem fez: _______________
- Tudo funcionando: [ ] SIM [ ] COM PROBLEMAS [ ] NÃO

Se com problemas, descreva:
_________________________________________________________________
_________________________________________________________________

