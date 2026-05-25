# 🔐 Referência de Variáveis de Ambiente

**Copie e cole estas variáveis exatamente no EasyPanel Dashboard.**

> ⚠️ **IMPORTANTE:** Substitua os placeholders `[POSTGRES_HOSTNAME]`, `[REDIS_HOSTNAME]`, `[MINIO_HOSTNAME]` pelos valores **reais** fornecidos pelo EasyPanel após criar os serviços.

---

## 📋 Valores Padrão (Copie Exatos)

| Nome da Var | Valor | Notas |
|---|---|---|
| `SECRET_KEY` | `k8xAmP9xvQ2rL5xnJ4wH7cF3bG6yT1Z` | Mude em produção real |
| `DEBUG` | `False` | Nunca deixe `True` em prod |
| `ENV` | `production` | Ou `development` se testing |
| `LOG_LEVEL` | `INFO` | Ou `DEBUG` para troubleshoot |
| `MINIO_ROOT_USER` | `minioadmin` | Padrão MinIO |
| `MINIO_ROOT_PASSWORD` | `FiscalAI#MinIO2026!@Secure` | Pode mudar |
| `MINIO_BUCKET` | `fiscalai-documents` | Nome do bucket |
| `POSTGRES_USER` | `fiscalai_user` | User do banco |
| `POSTGRES_PASSWORD` | `FiscalAI#Postgres2026!` | Senha do banco |
| `POSTGRES_DB` | `fiscalai_db` | Database name |

---

## 🔗 Variáveis que Dependem de Hostnames do EasyPanel

Após criar PostgreSQL, Redis e MinIO no EasyPanel, você receberá hostnames.

**Exemplo:**
```
PostgreSQL → postgres-123abc.easypanel.host
Redis → redis-456def.easypanel.host
MinIO → minio-789ghi.easypanel.host
```

**Substitua os valores abaixo:**

### Backend App — Environment Variables

```env
# DATABASE
DATABASE_URL=postgresql://fiscalai_user:FiscalAI#Postgres2026!@[POSTGRES_HOSTNAME]:5432/fiscalai_db

# REDIS
REDIS_URL=redis://[REDIS_HOSTNAME]:6379/0
CELERY_BROKER_URL=redis://[REDIS_HOSTNAME]:6379/1
CELERY_RESULT_BACKEND=redis://[REDIS_HOSTNAME]:6379/2

# MINIO
MINIO_ENDPOINT=[MINIO_HOSTNAME]:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=FiscalAI#MinIO2026!@Secure
MINIO_BUCKET=fiscalai-documents

# FASTAPI CONFIG
SECRET_KEY=k8xAmP9xvQ2rL5xnJ4wH7cF3bG6yT1Z
DEBUG=False
ENV=production
LOG_LEVEL=INFO

# CORS & HOSTS
CORS_ORIGINS=https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host,http://localhost:5173
ALLOWED_HOSTS=chatwoot-fiscalai-backend.6hjchk.easypanel.host,backend,localhost,127.0.0.1
```

---

### Frontend App — Environment Variables

```env
VITE_API_BASE_URL=https://chatwoot-fiscalai-backend.6hjchk.easypanel.host
NODE_ENV=production
```

---

## 🚀 Passo-a-Passo para Adicionar

### No Dashboard EasyPanel:

1. Vá para **Seu App** (ex: `fiscalai-backend`)
2. Clique na aba **Settings**
3. Procure por **Environment Variables**
4. Clique **Add Variable**
5. Cole cada linha acima (uma por uma, ou copie tudo de uma vez)

**Formato correto:**
```
KEY=VALUE
```

Exemplo:
```
SECRET_KEY=k8xAmP9xvQ2rL5xnJ4wH7cF3bG6yT1Z
DEBUG=False
```

6. Após adicionar todas, clique **Save**
7. App vai reiniciar automaticamente (aguarde 2-3 min)

---

## ✅ Checklist de Variáveis

### Backend
- [ ] `DATABASE_URL` — com [POSTGRES_HOSTNAME] correto
- [ ] `REDIS_URL` — com [REDIS_HOSTNAME] correto
- [ ] `CELERY_BROKER_URL` — com [REDIS_HOSTNAME] correto
- [ ] `CELERY_RESULT_BACKEND` — com [REDIS_HOSTNAME] correto
- [ ] `MINIO_ENDPOINT` — com [MINIO_HOSTNAME] correto
- [ ] `MINIO_ROOT_USER` — `minioadmin`
- [ ] `MINIO_ROOT_PASSWORD` — `FiscalAI#MinIO2026!@Secure`
- [ ] `MINIO_BUCKET` — `fiscalai-documents`
- [ ] `SECRET_KEY` — qualquer valor aleatório
- [ ] `DEBUG` — `False`
- [ ] `ENV` — `production`
- [ ] `LOG_LEVEL` — `INFO`
- [ ] `CORS_ORIGINS` — correto (frontend URL)
- [ ] `ALLOWED_HOSTS` — correto (backend URL)

### Frontend
- [ ] `VITE_API_BASE_URL` — URL exata do backend
- [ ] `NODE_ENV` — `production`

---

## 🔍 Como Encontrar Hostnames do EasyPanel

Após criar cada serviço, EasyPanel mostra a URL no dashboard:

### PostgreSQL
1. Dashboard → **Services**
2. Clique em `fiscalai-postgres`
3. Procure por **Connection String** ou **Host**
4. Copie apenas a parte `hostname` (ex: `postgres-abc123.easypanel.host`)

### Redis
1. Dashboard → **Services**
2. Clique em `fiscalai-redis`
3. Procure por **Host**
4. Copie (ex: `redis-abc123.easypanel.host`)

### MinIO
1. Se MinIO for App Docker:
   - Dashboard → Apps → `fiscalai-minio`
   - Procure por URL ou hostname (ex: `minio-abc123.easypanel.host`)

2. Se MinIO for Serviço Gerenciado:
   - Dashboard → Services → `fiscalai-minio`
   - Procure por **Endpoint** (ex: `minio.6hjchk.easypanel.host`)

---

## 🐛 Erros Comuns e Fixes

| Erro | Causa | Solução |
|---|---|---|
| `502 Bad Gateway` | `DATABASE_URL` com hostname errado | Verifique [POSTGRES_HOSTNAME] |
| `Cannot connect to redis` | `REDIS_URL` errada | Verifique [REDIS_HOSTNAME] |
| `CORS error` no browser | `CORS_ORIGINS` não inclui frontend | Adicione URL exata do frontend |
| Arquivo não salva | MinIO indisponível | Verifique `MINIO_ENDPOINT` e credenciais |
| `ModuleNotFoundError` | Dependência faltando | Verificar `requirements.txt` e Dockerfile |

---

## 💾 Backup de Variáveis

Se quiser salvar suas variáveis após criar (para não perder), copie daqui:

```
Criado em: _______________
Postgres Hostname: _______________
Redis Hostname: _______________
MinIO Hostname: _______________

Backend URL: _______________
Frontend URL: _______________
```

---

## 🔐 Segurança em Produção

**NUNCA commit variáveis sensíveis no GitHub!**

Arquivo `.gitignore` deve incluir:
```
.env
.env.local
.env.production
```

Variáveis sensíveis devem estar **apenas** no EasyPanel Dashboard (não no código).

---

