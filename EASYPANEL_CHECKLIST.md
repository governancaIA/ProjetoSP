# ? FiscalAI � Checklist R�pido EasyPanel

> Substitui EASYPANEL_MANUAL_SETUP.md com passos ultra-resumidos

---

## ?? 3 MINUTOS DE SETUP

### 1. GitHub Push (1 min)

```powershell
cd C:\Projetos\learn
git push origin main
# Se SSH falhar ? usar HTTPS + Personal Access Token
```

**Alternativa HTTPS:**
```powershell
git remote set-url origin https://github.com/seu-usuario/seu-repo.git
git config --global credential.helper store  # Salva credenciais
git push origin main
# Digitar usuario + token quando pedir
```

---

### 2. Backend App no EasyPanel (1 min)

1. **EasyPanel Dashboard**
2. **+ New App** (ou + Create ? App)
3. **Preencher:**

```
Name:                 fiscalai-backend
GitHub Repo:          seu-usuario/seu-repo
Branch:               main
Build Context:        .
Dockerfile:           backend/Dockerfile
Port (Internal):      8000
Port (External):      8000
```

⚠️ **IMPORTANTE:**
- Build Context DEVE ser `.` (raiz do repo)
- Dockerfile DEVE ser `backend/Dockerfile` (sem `./`)

4. **Environment Variables** ? Copiar e colar tudo:

```env
DEBUG=false
DATABASE_URL=postgresql://postgres:cnfcnn4xbwv7eecahjly@chatwoot_bancosped:5432/sped?sslmode=disable
REDIS_URL=redis://default:JIANkalu@123@chatwoot_async:6379
CELERY_BROKER_URL=redis://default:JIANkalu@123@chatwoot_async:6379/0
CELERY_RESULT_BACKEND=redis://default:JIANkalu@123@chatwoot_async:6379/1
MINIO_ENDPOINT=chatwoot-minio.6hjchk.easypanel.host
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password
MINIO_USE_SSL=true
CORS_ORIGINS=["https://fiscalai.6hjchk.easypanel.host"]
SECRET_KEY=fiscal-ai-prod-key-12345678901234567890
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
LOG_LEVEL=INFO
```

5. **Create** ? deixar buildar (5-10 min)

---

### 3. Frontend App no EasyPanel (1 min)

1. **+ New App**
2. **Preencher:**

```
Name:                 fiscalai-frontend
GitHub Repo:          seu-usuario/seu-repo
Branch:               main
Build Context:        .
Dockerfile:           frontend/Dockerfile.prod
Port (Internal):      80
Port (External):      80
```

⚠️ **IMPORTANTE:**
- Build Context DEVE ser `.` (raiz do repo)
- Dockerfile DEVE ser `frontend/Dockerfile.prod` (sem `./`)

3. **Environment Variables:**

```env
VITE_API_BASE_URL=https://fiscalai-backend.6hjchk.easypanel.host/api
```

4. **Create** ? deixar buildar

---

## ? Checklist P�s-Deploy

- [ ] Backend build completado (sem erros)
- [ ] Frontend build completado (sem erros)
- [ ] Backend domain criado: `fiscalai-backend.6hjchk.easypanel.host`
- [ ] Frontend domain criado: `fiscalai.6hjchk.easypanel.host`
- [ ] SSL ativado em ambos
- [ ] Backend respondendo: `curl https://fiscalai-backend.6hjchk.easypanel.host/health`
- [ ] Frontend respondendo: `curl https://fiscalai.6hjchk.easypanel.host/health`
- [ ] Frontend carregando: `https://fiscalai.6hjchk.easypanel.host` (browser)
- [ ] Login page aparecendo
- [ ] API respondendo ao tentar login

---

## ?? Se Algo Falhar

**Backend build com erro:**
```
Logs ? Build Logs ? procurar erro
Geralmente: requirements.txt, imports, ou env vars
Corrigir localmente, fazer git push, clicar Rebuild
```

**Frontend build com erro:**
```
Logs ? Build Logs ? procurar erro
Geralmente: npm, Dockerfile.prod, ou nginx.conf
Verificar que frontend/Dockerfile.prod existe
Verificar que frontend/nginx.conf existe
```

**Conex�o recusada ao banco:**
```
Verificar DATABASE_URL em env vars
Confirmar que PostgreSQL remoto est� acess�vel
psql postgresql://postgres:senha@chatwoot_bancosped:5432/sped
```

---

## ?? URLs Finais

```
Frontend:       https://fiscalai.6hjchk.easypanel.host
Backend API:    https://fiscalai-backend.6hjchk.easypanel.host
API Docs:       https://fiscalai-backend.6hjchk.easypanel.host/docs
Health:         https://fiscalai-backend.6hjchk.easypanel.host/health
```

---

## ?? Pr�ximas A��es

1. ? Git push
2. ? Criar 2 apps (backend + frontend)
3. ? Esperar build
4. ? Testar acesso
5. ?? Pronto!

---

## ?? Problemas?

Consulte:
- `EASYPANEL_TROUBLESHOOT.md` (diagn�stico completo)
- `DOCKER_SETUP.md` (testar localmente antes)
