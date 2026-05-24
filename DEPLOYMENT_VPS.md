# FiscalAI — Deploy no VPS Hostinger

## ?? Visão Geral

Este guia cobre o deploy da stack FiscalAI completa (PostgreSQL, Redis, MinIO, FastAPI, Celery, React) no VPS Hostinger usando Docker Compose.

---

## ?? Pré-requisitos

### 1. Acesso ao VPS Hostinger
- **Host:** seu_vps.com ou IP
- **SSH User:** root ou usuário criado
- **SSH Key:** gerada no painel Hostinger

### 2. Verificar Ambiente

Conectar ao VPS:
```bash
ssh -i sua_chave.pem root@seu_vps_ip
```

Verificar Docker:
```bash
docker --version
docker-compose --version
```

Se não tiver Docker instalado:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

## ?? Etapa 1: Preparar VPS

### 1.1 Criar diretório de projeto

```bash
mkdir -p /var/www/fiscalai
cd /var/www/fiscalai
```

### 1.2 Clonar repositório

```bash
git clone https://github.com/seu-usuario/fiscalai.git .
```

### 1.3 Criar .env a partir de .env.example

```bash
cp .env.example .env
```

### 1.4 Atualizar variáveis para produção

```bash
nano .env  # ou vim
```

**Variáveis CRÍTICAS a alterar:**

```env
# Database (usar o mesmo Postgres que você tem)
DATABASE_URL=postgresql://postgres:cnfcnn4xbwv7eecahjly@chatwoot_bancosped:5432/sped?sslmode=disable

# Redis (usar seu Redis remoto)
REDIS_URL=redis://default:JIANkalu@123@chatwoot_async:6379
CELERY_BROKER_URL=redis://default:JIANkalu@123@chatwoot_async:6379/0
CELERY_RESULT_BACKEND=redis://default:JIANkalu@123@chatwoot_async:6379/1

# MinIO (usar seu MinIO cloud)
MINIO_ENDPOINT=chatwoot-minio.6hjchk.easypanel.host
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password
MINIO_USE_SSL=true

# SEGURANÇA
DEBUG=false
SECRET_KEY=generate-uma-chave-segura-128-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (ajustar para seu domínio)
CORS_ORIGINS=["https://seu-dominio.com", "https://www.seu-dominio.com"]

# Frontend (apontar para o domínio real)
VITE_API_BASE_URL=https://seu-dominio.com/api
```

**Gerar SECRET_KEY segura:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## ?? Etapa 2: Docker Compose em Produção

### 2.1 Criar docker-compose.prod.yml

```bash
# Copiar arquivo de desenvolvimento
cp docker-compose.yml docker-compose.prod.yml
```

### 2.2 Editar docker-compose.prod.yml

Mudanças para produção:

```yaml
# Remover hot-reload do backend
backend:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000
  # SEM --reload em produção!

# Frontend em modo build (nginx)
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile.prod
  command: npm run build
  # Será servido por nginx reverse proxy
```

### 2.3 Iniciar stack em produção

```bash
# Parar qualquer container anterior
docker-compose down

# Iniciar nova stack (sem build se já buildou)
docker-compose -f docker-compose.prod.yml up -d

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f backend
```

---

## ?? Etapa 3: Reverse Proxy (nginx)

FiscalAI roda em containers, mas precisa ser acessível via https no domínio.

### 3.1 Instalar nginx

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 3.2 Criar configuração nginx

```bash
sudo nano /etc/nginx/sites-available/fiscalai
```

Adicionar:

```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:5173;  # ou nginx na porta 80 se build
}

server {
    listen 80;
    server_name seu-dominio.com www.seu-dominio.com;

    # Redirecionar HTTP para HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name seu-dominio.com www.seu-dominio.com;

    # Certificado SSL (será gerado por certbot)
    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    # API Backend
    location /api/ {
        proxy_pass http://backend/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend
    location / {
        proxy_pass http://frontend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3.3 Ativar configuração

```bash
sudo ln -s /etc/nginx/sites-available/fiscalai /etc/nginx/sites-enabled/
sudo nginx -t  # validar
sudo systemctl restart nginx
```

### 3.4 Gerar certificado SSL (Let's Encrypt)

```bash
sudo certbot certonly --nginx -d seu-dominio.com -d www.seu-dominio.com

# Auto-renovar
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## ?? Etapa 4: Banco de Dados

Seu `DATABASE_URL` aponta para `chatwoot_bancosped` (remoto).

### 4.1 Verificar conectividade

```bash
# Testar conexão (do container)
docker-compose exec backend psql -U postgres -h chatwoot_bancosped -d sped -c "SELECT 1"
```

### 4.2 Criar tables (se primeira execução)

```bash
# Backend vai criar tables automaticamente no startup
docker-compose logs -f backend | grep "create_all"
```

### 4.3 Backup do database

```bash
# Backup manual
pg_dump -U postgres -h chatwoot_bancosped -d sped > backup.sql

# Restaurar
psql -U postgres -h chatwoot_bancosped -d sped < backup.sql
```

---

## ??? Etapa 5: Redis e MinIO

### 5.1 Verificar Redis

```bash
# Testar conexão
docker-compose exec backend redis-cli -h chatwoot_async -a "JIANkalu@123" PING
```

### 5.2 Verificar MinIO

```bash
# Testar conexão
docker-compose exec backend python -c "
from minio import Minio
m = Minio('chatwoot-minio.6hjchk.easypanel.host', 
          access_key='admin', secret_key='password', secure=True)
print('MinIO OK')
"
```

---

## ?? Etapa 6: Monitoramento

### 6.1 Logs em tempo real

```bash
# Todos os logs
docker-compose logs -f

# Apenas backend
docker-compose logs -f backend

# Apenas worker
docker-compose logs -f celery-worker
```

### 6.2 Flower (Celery Monitoring)

Acessar: `https://seu-dominio.com/flower`

(Precisa adicionar nginx rule para /flower ? localhost:5555)

### 6.3 Health Check

```bash
# API respondendo?
curl https://seu-dominio.com/health

# Frontend carregando?
curl https://seu-dominio.com/ | head -20
```

---

## ?? Troubleshooting

### Backend não conecta ao PostgreSQL

```bash
# Verificar URL
docker-compose exec backend env | grep DATABASE

# Testar conexão manual
docker-compose exec backend psql $DATABASE_URL -c "SELECT 1"
```

### Redis desconectado

```bash
# Verificar conexão
docker-compose exec backend redis-cli -h chatwoot_async ping

# Check password
redis-cli -h chatwoot_async -a "JIANkalu@123" ping
```

### MinIO bucket não existe

```bash
# Criar bucket
docker-compose exec backend python << 'EOF'
from minio import Minio
from minio.error import S3Error

m = Minio('chatwoot-minio.6hjchk.easypanel.host',
          access_key='admin', secret_key='password', secure=True)

try:
    m.make_bucket('fiscalai-documents')
    print('Bucket created')
except S3Error as e:
    print(f'Error: {e}')
EOF
```

### Frontend não carrega

```bash
# Verificar se está sendo servido
curl -I https://seu-dominio.com/

# Check logs nginx
sudo tail -f /var/log/nginx/error.log
```

---

## ?? Segurança em Produção

### 1. Firewall

```bash
sudo ufw allow 22      # SSH
sudo ufw allow 80      # HTTP
sudo ufw allow 443     # HTTPS
sudo ufw enable
```

### 2. Variáveis Sensíveis

```bash
# NUNCA commitar .env no Git!
git status | grep .env
# Não deve listar .env ou .env.local

# Verificar .gitignore
cat .gitignore | grep .env
```

### 3. Debug Mode

```bash
# NUNCA em produção!
DEBUG=true  # ? ERRADO

# Sempre
DEBUG=false  # ? CORRETO
```

### 4. CORS

```bash
# Específico para seu domínio
CORS_ORIGINS=["https://seu-dominio.com"]

# NÃO usar wildcard
CORS_ORIGINS=["*"]  # ? ERRADO EM PRODUÇÃO
```

---

## ?? Escalar para Produção

### 1. Load Balancer

Se tiver muito tráfego, usar load balancer (nginx upstream):

```nginx
upstream backend_servers {
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}

location /api/ {
    proxy_pass http://backend_servers;
}
```

### 2. Auto-restart

```bash
# docker-compose restart automático
docker-compose up -d --restart=always

# ou systemd
sudo systemctl enable docker
```

### 3. Backups Automáticos

```bash
# Script de backup diário
0 2 * * * /var/www/fiscalai/backup.sh
```

---

## ? Checklist Final

- [ ] Docker + Docker Compose instalados no VPS
- [ ] Repositório clonado em `/var/www/fiscalai`
- [ ] `.env` configurado com credenciais reais
- [ ] PostgreSQL remoto acessível
- [ ] Redis remoto acessível
- [ ] MinIO remoto acessível e bucket criado
- [ ] docker-compose up rodando
- [ ] nginx configurado como reverse proxy
- [ ] Certificado SSL (Let's Encrypt) ativo
- [ ] Frontend acessível em https://seu-dominio.com
- [ ] API respondendo em https://seu-dominio.com/api
- [ ] Health check OK: curl https://seu-dominio.com/health
- [ ] Logs monitoráveis: docker-compose logs -f
- [ ] DEBUG=false em .env
- [ ] SECRET_KEY gerada e segura
- [ ] Firewall configurado
- [ ] Backups automatizados

---

## ?? Você está pronto para produção!

Depois de validar tudo:
1. ? Push código para GitHub
2. ? Pull no VPS
3. ? Validar .env
4. ? docker-compose up -d
5. ? Acessar https://seu-dominio.com

---

## Suporte

Problemas? Verifique:
1. `docker-compose logs backend` — erros do backend
2. `docker-compose logs celery-worker` — tarefas assíncronas
3. `sudo tail -f /var/log/nginx/error.log` — nginx
4. `curl https://seu-dominio.com/health` — API viva?
