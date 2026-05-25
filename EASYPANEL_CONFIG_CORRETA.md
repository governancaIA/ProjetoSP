# ✅ Configuração Correta no EasyPanel

## Problema Identificado

Os deploys falham em 1–6 segundos porque:
1. **Frontend**: usando `Dockerfile` (dev) em vez de `Dockerfile.prod` (nginx/produção)
2. **Backend**: Build Context incorreto — Docker não acha `requirements.txt`
3. **nginx.conf**: hostname do backend estava errado (`backend` → corrigido para `back`)

---

## 🖥️ Serviço: `fiscalia-front` (Frontend)

Acesse o serviço no EasyPanel → **Settings** → **Build**

| Campo | Valor |
|---|---|
| **Source** | GitHub repo |
| **Branch** | `main` |
| **Build Context** | `frontend` |
| **Dockerfile** | `frontend/Dockerfile.prod` |
| **Port** | `80` |

> ⚠️ **Crítico**: Build Context deve ser `frontend` (não `.` e não vazio)

**Sem variáveis de ambiente necessárias** — a URL da API é relativa (`/api/v1`), o nginx faz o proxy para o backend.

---

## ⚙️ Serviço: `back` (Backend)

Acesse o serviço no EasyPanel → **Settings** → **Build**

| Campo | Valor |
|---|---|
| **Source** | GitHub repo |
| **Branch** | `main` |
| **Build Context** | `backend` |
| **Dockerfile** | `backend/Dockerfile` |
| **Port** | `8000` |

### Variáveis de Ambiente obrigatórias:

Vá em **Settings** → **Environment**:

```
DATABASE_URL=postgresql://fiscalai_user:SUA_SENHA@postgres:5432/fiscalai_db
SECRET_KEY=gere-uma-chave-forte-aqui
DEBUG=False
CORS_ORIGINS=["https://SEU-DOMINIO-FRONTEND.easypanel.host"]
```

---

## 🗄️ Serviço: PostgreSQL (obrigatório)

Se ainda não criou, no EasyPanel → **+ New Service** → **PostgreSQL**

| Campo | Valor |
|---|---|
| **Name** | `postgres` |
| **DB Name** | `fiscalai_db` |
| **User** | `fiscalai_user` |
| **Password** | (crie uma senha forte) |

Após criar, copie a **Connection String** interna e cole em `DATABASE_URL` do backend.

---

## 🔄 Passo a Passo para Corrigir Agora

### 1. Frontend (`fiscalia-front`)
1. Clique em **fiscalia-front** → **Settings**
2. Na seção **Build**:
   - Build Context: `frontend`
   - Dockerfile: `frontend/Dockerfile.prod`
3. Clique **Save**
4. Clique **Redeploy**

### 2. Backend (`back`)
1. Clique em **back** → **Settings**
2. Na seção **Build**:
   - Build Context: `backend`
   - Dockerfile: `backend/Dockerfile`
3. Na seção **Environment**, adicione as variáveis acima
4. Clique **Save**
5. Clique **Redeploy**

---

## ✅ Como Saber que Funcionou

**Backend ok:**
```
https://back.SEU-PROJETO.easypanel.host/health
→ {"status":"healthy","service":"FiscalAI API"}
```

**Frontend ok:**
```
https://fiscalia-front.SEU-PROJETO.easypanel.host
→ Abre a tela de login do FiscalAI
```

**Proxy ok** (frontend chamando backend):
```
https://fiscalia-front.SEU-PROJETO.easypanel.host/api/v1/health
→ {"status":"healthy","service":"FiscalAI API"}
```

---

## 🚨 Se o Backend ainda falhar após o Build

Significa que está tentando conectar no PostgreSQL. Verifique:

1. O serviço `postgres` está **Running** no EasyPanel
2. A `DATABASE_URL` usa o hostname `postgres` (nome interno do serviço)
3. As credenciais batem com as configuradas no serviço PostgreSQL

Execute as migrations após o primeiro deploy bem-sucedido:
```bash
# No terminal do EasyPanel (ou via SSH):
docker exec -it <container-id-do-back> alembic upgrade head
```
