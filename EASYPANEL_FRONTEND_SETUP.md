# FiscalAI Frontend — Setup no EasyPanel

## ?? Resumo

O frontend (React + Vite) precisa ser deployado no EasyPanel como uma segunda aplicação.

**Arquitetura:**
```
Frontend (EasyPanel App 1) — :80 (nginx)
   ? (proxya para)
Backend (EasyPanel App 2) — :8000 (FastAPI)
```

---

## ?? Passo 1: Criar Nova App para Frontend

### No EasyPanel Dashboard:

1. **Criar nova aplicação:**
   - Clique em **"Create new app"**
   - Name: `fiscalai-frontend`
   - Repository: seu_repo (mesmo do backend)
   - Branch: `main`

2. **Configurar build:**
   - Build context: `./frontend`
   - Dockerfile: `./frontend/Dockerfile.prod`
   - Port: `80` (nginx vai rodar na porta 80)

3. **Environment variables:**

```env
# Apontar para o backend
VITE_API_BASE_URL=https://seu-dominio.com/api
```

Ou se backend também está no EasyPanel:
```env
VITE_API_BASE_URL=https://seu-dominio-backend.com/api
```

---

## ?? Passo 2: Verificar Dockerfiles

### Frontend Dockerfile.prod

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

? Já criado em: `frontend/Dockerfile.prod`

### Frontend nginx.conf

```nginx
user nginx;
worker_processes auto;

http {
    # ... gzip, MIME types, etc...

    server {
        listen 80;
        root /usr/share/nginx/html;
        index index.html;

        # SPA routing
        location / {
            try_files $uri $uri/ /index.html;
        }

        # Proxy para API
        location /api/ {
            proxy_pass http://backend:8000/api/;
        }

        # Health check
        location /health {
            return 200 '{"status":"healthy"}';
        }
    }
}
```

? Já criado em: `frontend/nginx.conf`

---

## ?? Configuração no EasyPanel

### Abrir: Frontend App ? Settings

#### General

| Campo | Valor |
|-------|-------|
| **App Name** | fiscalai-frontend |
| **Git Repository** | seu_repo |
| **Branch** | main |
| **Build Context** | ./frontend |
| **Dockerfile** | ./frontend/Dockerfile.prod |

#### Ports

| Internal | External |
|----------|----------|
| 80 | 80 (ou porta customizada) |

#### Environment Variables

```env
VITE_API_BASE_URL=https://seu-dominio.com/api
```

#### Volumes (Opcional)

Se quiser logs persistentes:
```
/var/log/nginx ? /data/nginx-logs
```

#### Health Check

- Path: `/health`
- Interval: 30s
- Timeout: 5s

---

## ?? Domains/DNS

### Associar domínio ao frontend

No EasyPanel:
1. **Frontend App ? Domains**
2. **Add domain**: `seu-dominio.com` (ou `www.seu-dominio.com`)
3. **SSL**: Let's Encrypt (automático)

### Se backend está em outro domínio:

Frontend `seu-dominio.com` proxya para:
- `seu-dominio-backend.com/api` (backend)

Configure no nginx.conf:
```nginx
location /api/ {
    proxy_pass https://seu-dominio-backend.com/api/;
}
```

---

## ? Verificar Deployment

### 1. Acessar frontend

```bash
curl https://seu-dominio.com/
# Esperado: HTML do React
```

### 2. Verificar health check

```bash
curl https://seu-dominio.com/health
# Esperado: {"status":"healthy"}
```

### 3. Testar conexão com API

No browser:
```
https://seu-dominio.com
? Abre login
? Tenta conectar em /api/auth/me
? Deve receber resposta do backend
```

### 4. Ver logs

```bash
EasyPanel UI:
Frontend App ? Logs ? Build Logs
Frontend App ? Logs ? Runtime Logs
```

---

## ?? Troubleshooting

### "Cannot GET /documents"

**Problema:** SPA routing não funcionando

**Solução:** Verificar nginx.conf contém:
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

### "API call failed" / "Connection refused"

**Problema:** Frontend não consegue conectar ao backend

**Solução:** 
1. Verificar `VITE_API_BASE_URL` em Environment Variables
2. Confirmar backend está rodando
3. Verificar CORS no backend:
   ```env
   CORS_ORIGINS=["https://seu-dominio.com"]
   ```

### "Nginx failed to build"

**Problema:** Dockerfile.prod com erro

**Solução:**
```bash
# Verificar localmente
docker build -f frontend/Dockerfile.prod .

# Ver erro específico
docker logs container_id
```

### Build timeout

**Problema:** `npm install` demorando

**Solução:** No EasyPanel, aumentar timeout:
- Settings ? Build ? Timeout: 1800s (30 min)

---

## ?? Performance em Produção

### 1. Gzip compression

? Já ativado em `nginx.conf`

### 2. Cache de assets

? Já configurado:
```nginx
location ~* \.(js|css)$ {
    expires 1y;
}
```

### 3. Image optimization

No seu código React, usar `<img loading="lazy">`

---

## ?? Estrutura Final

```
EasyPanel
+-- App 1: fiscalai-backend
¦   +-- Port: 8000
¦   +-- Domain: seu-dominio-backend.com (ou interno)
¦   +-- Type: FastAPI
¦
+-- App 2: fiscalai-frontend
    +-- Port: 80 (nginx)
    +-- Domain: seu-dominio.com
    +-- Type: React + Vite
    +-- Proxya para backend em /api/
```

---

## ?? Checklist Final

- [ ] Frontend Dockerfile.prod criado
- [ ] nginx.conf criado
- [ ] Nova app criada no EasyPanel
- [ ] Build context: `./frontend`
- [ ] Dockerfile: `./frontend/Dockerfile.prod`
- [ ] Environment: `VITE_API_BASE_URL` configurado
- [ ] Domínio associado
- [ ] SSL gerado (Let's Encrypt)
- [ ] Health check OK: `/health`
- [ ] Frontend acessível
- [ ] API respondendo
- [ ] Login funcionando

---

## ?? Próximas Ações

1. ? Push de `Dockerfile.prod` e `nginx.conf` para GitHub
2. ? Criar nova app no EasyPanel com configurações acima
3. ? Deixar buildar
4. ? Associar domínio
5. ? Testar acesso em `seu-dominio.com`
