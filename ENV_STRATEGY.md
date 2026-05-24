# FiscalAI — Environment Variables Strategy

## Visão Geral

O projeto usa uma estratégia de 3 camadas para gerenciar variáveis de ambiente:

```
.env.example (VERSIONADO)
    ?
    +-? Local Development: .env (NÃO VERSIONADO)
    ¦
    +-? Production: .env.local (NÃO VERSIONADO)
        +-? Docker Secrets / Terraform (VPS)
```

---

## 1. `.env.example` (Commitar no Git ?)

**Propósito:** Template com valores de desenvolvimento padrão

**O que contém:**
- Credenciais genéricas para dev (minioadmin/password)
- Hostnames Docker Compose (postgres:5432, redis:6379, minio:9000)
- Debug=true, CORS_ORIGINS=["*"]
- SECRET_KEY para desenvolvimento apenas

**Exemplo:**
```env
DATABASE_URL=postgresql://fiscalai_user:fiscalai_password_dev@postgres:5432/fiscalai_db
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
SECRET_KEY=fiscal-ai-development-key-change-in-production
DEBUG=true
```

**Quando atualizar:**
- Novo serviço adicionado
- Nova variável de configuração
- Mudança na arquitetura

---

## 2. `.env` (NÃO Commitar ?)

**Propósito:** Desenvolvimento local (variações personalizadas)

**Como usar:**
```powershell
# Criar a partir do template
copy .env.example .env

# Depois customizar se necessário (portas diferentes, DBs remotas, etc.)
```

**Exemplo (desenvolvimento local com docker-compose):**
```env
DATABASE_URL=postgresql://fiscalai_user:fiscalai_password_dev@postgres:5432/fiscalai_db
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
```

**Ignore in Git:** ? Já está em `.gitignore`

---

## 3. `.env.local` (NÃO Commitar ?)

**Propósito:** Credenciais reais para produção/staging

**O que contém:**
- Credenciais de produção (PostgreSQL remoto, Redis, MinIO cloud)
- SECRET_KEY real
- DEBUG=false
- CORS_ORIGINS com domínios reais

**Exemplo:**
```env
DATABASE_URL=postgresql://postgres:SENHA@chatwoot_bancosped:5432/sped?sslmode=disable
REDIS_URL=redis://default:SENHA@chatwoot_async:6379
MINIO_ENDPOINT=chatwoot-minio.6hjchk.easypanel.host
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=SENHA
SECRET_KEY=super-secret-production-key-128-chars
DEBUG=false
CORS_ORIGINS=["https://seu-dominio.com"]
```

**?? SEGURANÇA CRÍTICA:**
- NUNCA commitar este arquivo
- NUNCA fazer push com credenciais
- NUNCA compartilhar em chat/email
- Verificar `.gitignore` contém `.env.local` ?

**Quando usar:**
- Teste local antes de deploy no VPS
- Validação de integrações com serviços reais
- Debug de problemas em staging

**Ignore in Git:** ? Já está em `.gitignore`

---

## 4. Docker Compose (.env para dev)

Quando rodar `docker-compose up`, o Docker lê o `.env` (se existir):

```powershell
# Preparar
copy .env.example .env

# Iniciar
docker-compose up --build

# Docker usa variáveis de .env
# Frontend: VITE_API_BASE_URL=http://localhost:8000
# Backend: DATABASE_URL=postgresql://...@postgres:5432/...
```

---

## 5. VPS / Produção

**Nunca usar `.env` ou `.env.local` em produção!**

Usar **Docker Secrets** ou **variáveis de ambiente do sistema:**

```bash
# Opção 1: Docker Secrets (Swarm/Compose com secrets)
docker-compose -f docker-compose.prod.yml up

# Opção 2: Variáveis de ambiente do SO
export DATABASE_URL=postgresql://...
export SECRET_KEY=...
docker run -e DATABASE_URL -e SECRET_KEY ...

# Opção 3: Terraform / Infrastructure-as-Code
# Provisionar via Terraform (recomendado)
```

---

## Workflow por Ambiente

### 1?? Desenvolvimento Local (Docker Compose)

```powershell
# Setup inicial
copy .env.example .env
# .env contém: postgres:5432, redis:6379, minio:9000 (Docker names)

# Iniciar
docker-compose up --build

# Acessar
http://localhost:5173  # Frontend
http://localhost:8000  # Backend
```

### 2?? Teste Local (Credenciais Reais)

```powershell
# Se quiser testar com DB/Redis/MinIO reais
copy .env.example .env
# Editar .env com credenciais reais

# Rodar backend sem Docker
cd backend
python -m uvicorn app.main:app --reload

# Rodar frontend sem Docker
cd frontend
npm run dev
```

### 3?? VPS / Produção

```bash
# No VPS, usar variáveis de ambiente diretas (sem .env)
export DATABASE_URL=postgresql://...
export SECRET_KEY=...
# ... mais variáveis

# Iniciar com docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

---

## Checklist de Segurança

- [ ] `.env.local` **NÃO commitado** no Git
- [ ] `.env` **NÃO commitado** no Git (desenvolvimento local)
- [ ] `.env.example` **commitado** (template público)
- [ ] `.gitignore` contém `.env` e `.env.local`
- [ ] `SECRET_KEY` diferente para dev/prod
- [ ] Credenciais de produção **NUNCA em repositório**
- [ ] `DEBUG=false` em produção
- [ ] CORS_ORIGINS específico em produção

---

## Referência Rápida

| Arquivo | Versionado? | Contém | Onde Usar |
|---------|-----------|--------|-----------|
| `.env.example` | ? SIM | Template dev | Repositório |
| `.env` | ? NÃO | Dev local customizado | Máquina local |
| `.env.local` | ? NÃO | Credenciais reais | Antes de VPS |
| `docker-compose.yml` | ? SIM | Orquestração dev | Repositório |
| Variáveis do SO (VPS) | N/A | Credenciais produção | VPS |

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

Seu `.env` pode estar apontando para a DB errada. Verificar:
```env
DATABASE_URL=postgresql://fiscalai_user:fiscalai_password_dev@localhost:5432/fiscalai_db
```

### "Redis connection refused"

Seu `.env` pode estar apontando para Redis remoto (parado). Mudar para local:
```env
REDIS_URL=redis://localhost:6379/0
```

### "Credenciais inválidas"

Não commitou `.env.local` por acidente? Verificar:
```bash
git status | grep ".env"
# Não deve listar .env.local ou .env
```

---

## Próximas Etapas

1. ? Revisar `.env.example` (template commitado)
2. ? Criar `.env` para desenvolvimento (não-commitado)
3. ? Criar `.env.local` para teste com credenciais reais (não-commitado)
4. ?? Documentar processo no README principal
5. ?? Deploy no VPS (usar Docker Secrets / Terraform)
