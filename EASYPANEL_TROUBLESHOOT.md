# FiscalAI — Troubleshooting EasyPanel

## ?? Diagnóstico de Problemas

### 1. URL Incorreta

**Sintomas:**
- MinIO console não acessível
- Conexão recusada ao MinIO
- Bucket não criado

**Causas comuns:**
- URL digitada errado (typo)
- Protocolo errado (http vs https)
- Porta errada (:9000, :9001, etc.)
- Serviço não iniciou

**Solução:**

```bash
# Acessar EasyPanel
# https://seu-easypanel.host

# Verificar containers rodando:
# App ? Services ? Ver status

# Verificar URLs:
# App ? App Config ? Environment Variables
# Procurar: MINIO_ENDPOINT, MINIO_SERVER_URL

# URL correta deve ser:
MINIO_SERVER_URL=https://chatwoot-minio.6hjchk.easypanel.host
MINIO_ENDPOINT=chatwoot-minio.6hjchk.easypanel.host:9000
```

---

### 2. EasyPanel Não Subiu os Containers

**Sintomas:**
- "Deployment failed"
- Containers não rodando
- Erro ao fazer push

**Causas comuns:**
- Docker daemon não respondendo
- Espaço em disco insuficiente
- Erro de configuração
- Repositório Git não acessível

**Solução:**

```bash
# Via EasyPanel UI:
# 1. App ? Logs ? Ver erro exato
# 2. App ? Rebuild ? Tentar novamente
# 3. Se persistir: Delete app e recrie

# Via SSH no EasyPanel:
ssh seu_usuario@seu_easypanel_ip
docker ps  # Verificar containers
docker logs nome_container  # Ver erro específico
```

---

## ? Checklist de Configuração

### Passo 1: Variáveis de Ambiente Corretas

No EasyPanel, ir para:
**App ? Settings ? Environment Variables**

Verificar:

```env
# MinIO
MINIO_ENDPOINT=chatwoot-minio.6hjchk.easypanel.host
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=sua_senha
MINIO_USE_SSL=true
MINIO_SERVER_URL=https://chatwoot-minio.6hjchk.easypanel.host

# Redis
REDIS_URL=redis://default:sua_senha@chatwoot_async:6379

# PostgreSQL
DATABASE_URL=postgresql://postgres:sua_senha@chatwoot_bancosped:5432/sped

# FastAPI
DEBUG=false
SECRET_KEY=sua_chave_segura

# CORS
CORS_ORIGINS=["https://seu-dominio.com"]
```

### Passo 2: Dockerfile Correto

No EasyPanel, verificar:
**App ? Settings ? Dockerfile**

Deve conter:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Passo 3: Ports Mapeadas

No EasyPanel:
**App ? Ports**

Deve ter:
- 8000 ? Backend FastAPI
- 5173 ? Frontend (se tiver)

---

## ?? Opções de Recuperação

### Opção A: Corrigir Configuração Existente

1. EasyPanel ? App ? Settings
2. Corrigir variáveis de ambiente
3. EasyPanel ? Rebuild
4. Aguardar deployment

### Opção B: Deletar e Recriar do Zero

```bash
# No EasyPanel UI:
1. App ? Delete
2. Confirmar
3. Esperar limpeza
4. Criar nova app:
   - Name: fiscalai-backend
   - Git: seu_repo
   - Branch: main
   - Dockerfile: ./backend/Dockerfile
   - Ports: 8000
   - Environment: copiar de DEPLOYMENT_VPS.md
```

### Opção C: Deploy Local Antes

```bash
# Testar tudo localmente primeiro
docker-compose up --build

# Só depois de validar, fazer push para EasyPanel
```

---

## ?? Logs para Diagnosticar

### Via EasyPanel UI

```
App ? Logs ? Build Logs
App ? Logs ? Runtime Logs
```

### Via SSH

```bash
ssh seu_usuario@seu_easypanel_ip

# Ver containers
docker ps -a

# Ver logs
docker logs backend_container_name -f

# Verificar volume
docker volume ls
docker volume inspect nome_volume
```

---

## ?? Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| `Connection refused` | Porta errada | Verificar MINIO_ENDPOINT, REDIS_URL |
| `Build failed` | Dockerfile erro | Verificar `backend/Dockerfile` |
| `Out of space` | Disco cheio | Limpar volumes antigos |
| `Git access denied` | Credenciais Git | Gerar Personal Access Token |
| `Health check failed` | Aplicação não saudável | Ver `docker logs` |

---

## ?? Próximas Ações

1. **Coletar informações:**
   - Que URL específica saiu errada?
   - Qual erro aparece no EasyPanel?
   - Logs disponíveis?

2. **Decidir abordagem:**
   - Corrigir existente?
   - Recriar do zero?
   - Testar localmente primeiro?

3. **Implementar solução**

---

## ?? Recomendação

**Antes de tentar no EasyPanel novamente:**

1. ? Testar tudo localmente com docker-compose
2. ? Validar .env está correto
3. ? Confirmar backend sobe sem erros
4. ? Depois fazer push para EasyPanel

Isso evita retrabalho!
