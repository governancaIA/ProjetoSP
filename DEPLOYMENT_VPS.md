# FiscalAI — Deploy no VPS Hostinger

**VPS:** adriner.fr (89.116.214.246) — Hostinger KVM 2  
**URL produção:** https://adriner.fr/fiscalia  
**Stack:** Docker Compose + nginx + Let's Encrypt

---

## Pré-requisitos

- Acesso SSH ao VPS: `ssh -i ~/.ssh/id_ed25519 root@89.116.214.246`
- Docker + Docker Compose v2 instalados (ver Passo 0)
- Repositório no GitHub com GitHub Actions configurado

---

## Passo 0 — Preparar VPS (primeira vez)

```bash
# Conectar
ssh -i ~/.ssh/id_ed25519 root@89.116.214.246

# Instalar dependências
apt-get update && apt-get upgrade -y
apt-get install -y docker.io curl git nginx certbot python3-certbot-nginx

# Docker Compose v2
curl -sL "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

systemctl start docker && systemctl enable docker

# Clonar repositório
mkdir -p /opt/fiscalai
cd /opt/fiscalai
git clone https://github.com/governancaIA/ProjetoSP.git .
```

---

## Passo 1 — Configurar variáveis de ambiente

```bash
cd /opt/fiscalai/infra
cp .env.prod.example .env.prod
nano .env.prod
```

Variáveis críticas a alterar:

```env
# Segurança (OBRIGATÓRIO mudar)
SECRET_KEY=gere-com: python3 -c "import secrets; print(secrets.token_urlsafe(64))"
DEBUG=false

# Banco (usa PostgreSQL no próprio VPS via docker-compose.prod.yml)
DATABASE_URL=postgresql://fiscalai_user:SENHA_SEGURA@postgres:5432/fiscalai_db

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=SENHA_MINIO_SEGURA
MINIO_USE_SSL=false

# CORS
CORS_ORIGINS=https://adriner.fr

# Email alerts (opcional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu@email.com
SMTP_PASSWORD=app-password
ALERT_EMAIL_TO=destinatario@email.com
```

---

## Passo 2 — Deploy automático (script)

Execute no VPS:

```bash
cd /opt/fiscalai

# Atualizar código
git pull origin main

# Build e subir
cd infra
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Aguardar inicialização
sleep 30

# Verificar status
docker-compose -f docker-compose.prod.yml ps
```

---

## Passo 3 — nginx como reverse proxy

```bash
cat > /etc/nginx/sites-available/fiscalai << 'EOF'
upstream backend  { server localhost:8000; }
upstream frontend { server localhost:5173; }

server {
    listen 80;
    server_name adriner.fr www.adriner.fr;
    location /fiscalia { return 301 https://$server_name$request_uri; }
    location /         { return 301 https://$server_name$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name adriner.fr www.adriner.fr;

    ssl_certificate     /etc/letsencrypt/live/adriner.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/adriner.fr/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    client_max_body_size 2G;

    # FiscalAI frontend
    location /fiscalia/ {
        proxy_pass http://frontend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # FiscalAI API
    location /fiscalia/api/ {
        proxy_pass http://backend/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /fiscalia/health { proxy_pass http://backend/health; }

    location /fiscalia/flower/ {
        proxy_pass http://localhost:5555/;
        proxy_set_header Host $host;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/fiscalai /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

## Passo 4 — SSL (Let's Encrypt)

```bash
certbot certonly --nginx -d adriner.fr -d www.adriner.fr \
  --non-interactive --agree-tos --email admin@adriner.fr

# Auto-renovação
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && systemctl reload nginx") | crontab -
```

---

## Passo 5 — Firewall

```bash
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw --force enable
```

---

## CI/CD — GitHub Actions

O workflow `.github/workflows/deploy.yml` faz deploy automático a cada push na `main`:
1. Build e testa no GitHub
2. SSH no VPS → `git pull` → `docker-compose up -d --build`

Para atualizar manualmente:

```bash
cd /opt/fiscalai && git pull origin main
cd infra && docker-compose -f docker-compose.prod.yml up -d --build
```

---

## Monitoramento e manutenção

```bash
# Status dos containers
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml ps

# Logs em tempo real
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml logs -f backend

# Health check
curl https://adriner.fr/fiscalia/health

# Métricas Prometheus
curl https://adriner.fr/fiscalia/metrics

# Backup do banco
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml exec -T postgres \
  pg_dump -U fiscalai_user fiscalai_db > /opt/backups/db_$(date +%Y%m%d).sql

# Reiniciar serviço específico
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml restart backend
```

---

## Troubleshooting

| Sintoma | Diagnóstico | Solução |
|---|---|---|
| Backend não conecta ao PostgreSQL | `docker logs fiscalai-postgres` | Aguardar healthcheck (~30s) |
| `502 Bad Gateway` | nginx não alcança container | `docker ps` — verificar se backend está up |
| SSL error | Certificado expirado | `certbot renew --force-renewal && nginx -s reload` |
| Upload falha | MinIO sem bucket | `docker exec fiscalai-backend python -c "from app.core.storage import ensure_bucket; ensure_bucket()"` |
| Celery não processa | Redis desconectado | `docker-compose restart redis celery_worker` |

---

## Serviços em produção

| Serviço | URL |
|---|---|
| Frontend | https://adriner.fr/fiscalia |
| API Docs | https://adriner.fr/fiscalia/api/docs (dev only) |
| Health | https://adriner.fr/fiscalia/health |
| Flower | https://adriner.fr/fiscalia/flower |
| Prometheus | https://adriner.fr/fiscalia/metrics |
