# FiscalAI — Setup Manual no EasyPanel

Como a API do EasyPanel pode ter limitações, vamos fazer o setup manualmente via UI.

---

## ?? Checklist de Setup Passo-a-Passo

### PASSO 1: Preparar Código

```powershell
git add .
git commit -m "Deploy: FiscalAI completo com frontend e backend"
git push origin main
```

---

## PASSO 2: Criar Backend App

### No EasyPanel Dashboard:

1. **New Project** ? ou entrara em projeto existente
2. **Create new app**

**Configuração:**

| Campo | Valor |
|-------|-------|
| **Name** | fiscalai-backend |
| **Source** | GitHub |
| **Repository** | seu-usuario/fiscalai |
| **Branch** | main |
| **Root Directory** | backend |
| **Dockerfile** | ./backend/Dockerfile |

**Ports:**

| Internal | External |
|----------|----------|
| 8000 | 8000 |

**Environment Variables:**

Copiar e colar:

```env
DEBUG=false
API_TITLE=FiscalAI
API_VERSION=0.1.0
DATABASE_URL=postgresql://postgres:cnfcnn4xbwv7eecahjly@chatwoot_bancosped:5432/sped?sslmode=disable
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
REDIS_URL=redis://default:JIANkalu@123@chatwoot_async:6379
REDIS_CACHE_TTL=3600
MINIO_ENDPOINT=chatwoot-minio.6hjchk.easypanel.host
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password
MINIO_BUCKET_NAME=fiscalai-documents
MINIO_USE_SSL=true
CELERY_BROKER_URL=redis://default:JIANkalu@123@chatwoot_async:6379/0
CELERY_RESULT_BACKEND=redis://default:JIANkalu@123@chatwoot_async:6379/1
CELERY_TASK_TIME_LIMIT=3600
CELERY_TASK_SOFT_TIME_LIMIT=3000
CORS_ORIGINS=["https://fiscalai.6hjchk.easypanel.host"]
SECRET_KEY=fiscal-ai-production-secret-key-123456789
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
LOG_LEVEL=INFO
```

**Health Check:**

- Path: `/health`
- Interval: 30s
- Timeout: 5s
- Retries: 3

3. **Create** ? Deixar buildar

---

## PASSO 3: Criar Frontend App

1. **Create new app** (mesmo projeto)

**Configuração:**

| Campo | Valor |
|-------|-------|
| **Name** | fiscalai-frontend |
| **Source** | GitHub |
| **Repository** | seu-usuario/fiscalai |
| **Branch** | main |
| **Root Directory** | frontend |
| **Dockerfile** | ./frontend/Dockerfile.prod |

**Ports:**

| Internal | External |
|----------|----------|
| 80 | 80 |

**Environment Variables:**

```env
VITE_API_BASE_URL=https://fiscalai-backend.6hjchk.easypanel.host/api
```

**Health Check:**

- Path: `/health`
- Interval: 30s
- Timeout: 5s
- Retries: 3

3. **Create** ? Deixar buildar

---

## PASSO 4: Configurar Domains

### Para Backend:

1. Backend App ? **Domains**
2. **Add Domain**
   - Domain: `fiscalai-backend.6hjchk.easypanel.host`
   - SSL: ? Let's Encrypt

### Para Frontend:

1. Frontend App ? **Domains**
2. **Add Domain**
   - Domain: `fiscalai.6hjchk.easypanel.host`
   - SSL: ? Let's Encrypt

---

## PASSO 5: Verificar Build

### Status de Build:

1. App ? **Build Logs**
   - Procure por "Build completed successfully"

2. Se houver erro:
   - Verifique logs
   - Corrija no código
   - Faça git push
   - Clique **Rebuild**

---

## PASSO 6: Testar Acesso

### Backend:

```bash
# API respondendo?
curl https://fiscalai-backend.6hjchk.easypanel.host/health
# Esperado: {"status":"healthy","service":"FiscalAI API"}

# Swagger docs
https://fiscalai-backend.6hjchk.easypanel.host/docs
```

### Frontend:

```bash
# Frontend respondendo?
curl https://fiscalai.6hjchk.easypanel.host/health
# Esperado: {"status":"healthy"}

# Acessar
https://fiscalai.6hjchk.easypanel.host
```

### Full Test:

1. Acessar https://fiscalai.6hjchk.easypanel.host
2. Tela de login deve aparecer
3. Tentar login
4. Deve conectar ao backend em `/api/v1/auth/login`

---

## ?? Troubleshooting

### Build falha

**Erro:** `npm ERR! 404 Not Found`

**Solução:**
```bash
# Localmente
cd frontend
npm ci
npm run build
# Se falhar, corrigir e fazer push
```

**Erro:** `COPY failed: file not found`

**Solução:**
- Verificar path do Dockerfile
- Verificar `frontend/Dockerfile.prod` existe
- Verificar `frontend/nginx.conf` existe

---

### App não responde

**Erro:** `502 Bad Gateway`

**Solução:**
1. Verificar **Runtime Logs**
2. Procurar por erros
3. Verificar Environment Variables
4. Testar localmente: `docker-compose up`

---

### Conexão recusada ao banco

**Erro:** `psycopg.OperationalError: connection failed`

**Solução:**
- Verificar `DATABASE_URL` em env
- Confirmar PostgreSQL remoto está acessível
- Testar: `psql postgresql://postgres:senha@chatwoot_bancosped:5432/sped`

---

## ?? URLs Finais

```
Frontend:       https://fiscalai.6hjchk.easypanel.host
Backend API:    https://fiscalai-backend.6hjchk.easypanel.host
API Docs:       https://fiscalai-backend.6hjchk.easypanel.host/docs
API Health:     https://fiscalai-backend.6hjchk.easypanel.host/health
```

---

## ? Checklist Final

- [ ] Backend app criada no EasyPanel
- [ ] Frontend app criada no EasyPanel
- [ ] Build completado sem erros
- [ ] Domains associados e SSL ativo
- [ ] Backend respondendo em /health
- [ ] Frontend respondendo em /health
- [ ] Login página aparecer
- [ ] Pode fazer login
- [ ] Dashboard carregar dados

---

## ?? Próximas Ações

1. ? Seguir passos acima
2. ? Testar acesso
3. ? Criar usuários via POST /api/v1/auth/register (ou admin painel)
4. ? Upload de arquivos fiscais
5. ? Validação e scoring

---

## ?? Se Quiser Deletar Tudo e Começar do Zero

No EasyPanel:
1. App ? **Settings** ? **Delete**
2. Confirmar
3. Esparar limpeza
4. Criar novas apps (repetir passos acima)

---

## ?? Suporte

Se tiver dúvidas, consulte:
- `EASYPANEL_FRONTEND_SETUP.md`
- `EASYPANEL_TROUBLESHOOT.md`
- `DEPLOYMENT_VPS.md`
