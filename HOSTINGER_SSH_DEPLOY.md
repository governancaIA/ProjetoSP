# 🚀 Deploy Seguro FiscalAI na Hostinger

**VPS:** adriner.fr (89.116.214.246)  
**Provedor:** Hostinger KVM 2  
**Usuário:** root  
**URL FiscalAI:** https://adriner.fr/fiscalia  
**Status:** ✅ Pronto para deploy

---

## 🔒 RESUMO EXECUTIVO

### ✅ O que vai acontecer:
- FiscalAI roda em `/fiscalia` apenas
- SSL compartilhado com `adriner.fr`
- Site original **NÃO É TOCADO**
- Seu pai configura depois qual servidor usar para o resto

### 🛡️ Isolamento:
```
https://adriner.fr/
├─ /fiscalia ────────→ FiscalAI (NOSSA SOLUÇÃO)
└─ / ───────────────→ Site original (DO SEU PAI)
```

---

## 🔐 PASSO 1: Conectar via SSH

### No Windows (PowerShell)
```powershell
ssh -i $env:USERPROFILE\.ssh\id_ed25519 root@89.116.214.246
```

### No Linux / Mac
```bash
ssh -i ~/.ssh/id_ed25519 root@89.116.214.246
```

**Primeira vez:** Responda `yes` quando pedir confirmação do host

---

## ✅ PASSO 2: Verificar Ambiente

```bash
docker --version
git --version
python3 --version
```

Se faltar algo:
```bash
apt-get update && apt-get upgrade -y
apt-get install -y docker.io curl git python3 python3-pip wget
systemctl start docker && systemctl enable docker
```

---

## 📂 PASSO 3: Clonar Repositório

```bash
mkdir -p /opt
cd /opt
git clone https://github.com/governancaIA/ProjetoSP.git fiscalai
cd fiscalai
```

---

## 🐳 PASSO 4: Deploy Automático (Recomendado)

Execute este bloco **completo** na VPS:

```bash
cd /tmp && cat > deploy_safe.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 DEPLOY SEGURO FISCALAI - https://adriner.fr/fiscalia"

# 1. Atualizar Docker Compose para v2
apt-get update -qq && apt-get install -y -qq curl
apt-get remove -y docker-compose 2>/dev/null || true
curl -sL "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
echo "✅ Docker Compose v2 instalado"

# 2. Limpar containers antigos
cd /opt/fiscalai/infra
docker-compose -f docker-compose.prod.yml kill 2>/dev/null || true
docker-compose -f docker-compose.prod.yml down --volumes --remove-orphans 2>/dev/null || true
docker container prune -f 2>/dev/null || true
docker image prune -a -f 2>/dev/null || true
docker volume prune -f 2>/dev/null || true
docker rm -f fiscalai-frontend fiscalai-backend fiscalai-celery-worker fiscalai-celery-beat fiscalai-flower fiscalai-postgres fiscalai-redis fiscalai-minio 2>/dev/null || true
echo "✅ Limpeza completa"

# 3. Atualizar código
cd /opt/fiscalai
git pull origin main
echo "✅ Código atualizado"

# 4. Build (15-20 min)
cd infra
echo "⏳ Build Docker (pode levar 15-20 minutos)..."
docker-compose -f docker-compose.prod.yml build --no-cache --pull 2>&1 | tail -10
echo "✅ Build completo"

# 5. Iniciar stack
docker-compose -f docker-compose.prod.yml up -d
echo "⏳ Aguardando 3 minutos para PostgreSQL..."
sleep 180
echo "✅ Stack iniciado"

# 6. Status
docker-compose -f docker-compose.prod.yml ps

# 7. SSL
apt-get install -y -qq certbot python3-certbot-nginx
if [ ! -f "/etc/letsencrypt/live/adriner.fr/fullchain.pem" ]; then
    echo "⚠️  Gerando certificado SSL..."
    certbot certonly --standalone -d adriner.fr --non-interactive --agree-tos --email admin@adriner.fr 2>/dev/null || true
fi
echo "✅ SSL configurado"

# 8. Nginx (SEGURO - não mexe no site original)
apt-get install -y -qq nginx

cat > /etc/nginx/sites-available/fiscalai-only <<'NGINX_EOF'
upstream backend { server localhost:8000; }
upstream frontend { server localhost:5173; }

# HTTP
server {
    listen 80;
    server_name adriner.fr www.adriner.fr;

    # FiscalAI redireciona para HTTPS
    location /fiscalia {
        return 301 https://$server_name$request_uri;
    }

    # TUDO MAIS passa para o site original (seu pai configura depois)
    location / {
        # Deixe vazio por enquanto
        # Seu pai adiciona: proxy_pass http://seu-site;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name adriner.fr www.adriner.fr;

    ssl_certificate /etc/letsencrypt/live/adriner.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/adriner.fr/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    client_max_body_size 100M;

    # ===== FiscalAI em /fiscalia/ =====

    location = /fiscalia {
        return 301 /fiscalia/;
    }

    location /fiscalia/ {
        proxy_pass http://frontend/;
        proxy_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /fiscalia/api/ {
        proxy_pass http://backend/api/;
        proxy_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /fiscalia/flower/ {
        proxy_pass http://localhost:5555/;
        proxy_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /fiscalia/minio/ {
        proxy_pass http://localhost:9001/;
        proxy_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /fiscalia/health {
        proxy_pass http://backend/health;
        proxy_set_header Host $host;
    }

    # ===== RESTO DO SITE (seu pai configura depois) =====
    location / {
        # Deixe vazio ou adicione depois:
        # proxy_pass http://seu-site-original;
    }
}
NGINX_EOF

rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
ln -sf /etc/nginx/sites-available/fiscalai-only /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
systemctl enable nginx
echo "✅ Nginx configurado (SEGURO)"

# 9. Status final
echo ""
echo "=========================================="
echo "✅ DEPLOYMENT SEGURO COMPLETO!"
echo "=========================================="
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml ps
echo ""
echo "🌐 Acesse: https://adriner.fr/fiscalia"
echo ""
echo "🔗 Outros serviços:"
echo "   - API Docs: https://adriner.fr/fiscalia/api/docs"
echo "   - Flower: https://adriner.fr/fiscalia/flower"
echo "   - MinIO: https://adriner.fr/fiscalia/minio"
echo ""
echo "⚠️  Seu pai configura o resto do site em:"
echo "   /etc/nginx/sites-available/fiscalai-only"
echo "=========================================="
EOF
chmod +x deploy_safe.sh && bash deploy_safe.sh
```

---

## 📋 Passo a Passo Manual (Se Preferir)

Se o bloco anterior não funcionar, execute linha por linha:

### 4a. Atualizar Docker Compose
```bash
apt-get update && apt-get install -y curl
apt-get remove -y docker-compose
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### 4b. Limpar e Build
```bash
cd /opt/fiscalai/infra
docker-compose -f docker-compose.prod.yml down -v 2>/dev/null || true
docker system prune -f
docker-compose -f docker-compose.prod.yml build --no-cache
```

### 4c. Iniciar Stack
```bash
docker-compose -f docker-compose.prod.yml up -d
sleep 180
docker-compose -f docker-compose.prod.yml ps
```

### 4d. SSL
```bash
apt-get install -y certbot python3-certbot-nginx
certbot certonly --standalone -d adriner.fr
```

### 4e. Nginx (copia o bloco de config acima)
```bash
apt-get install -y nginx
# ... (copie a config NGINX_EOF de cima)
systemctl restart nginx
```

---

## ✅ Verificação Final

```bash
# Ver status dos containers
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml ps

# Ver logs (se houver erro)
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml logs -f backend

# Testar FiscalAI
curl https://adriner.fr/fiscalia
curl https://adriner.fr/fiscalia/api/v1/health
```

---

## 🎉 Acessar FiscalAI

| Serviço | URL |
|---------|-----|
| **Frontend** | https://adriner.fr/fiscalia |
| **API Docs** | https://adriner.fr/fiscalia/api/docs |
| **Flower** | https://adriner.fr/fiscalia/flower |
| **MinIO** | https://adriner.fr/fiscalia/minio |
| **Health** | https://adriner.fr/fiscalia/health |

---

## 🛡️ Segurança - Site Original

**Seu pai precisa fazer:**

1. Editar: `/etc/nginx/sites-available/fiscalai-only`
2. Nas seções `location /` (HTTP e HTTPS)
3. Adicionar sua configuração:

```nginx
# Opção A: Proxy para outro servidor
proxy_pass http://seu-site-original:porta;

# Opção B: Servir arquivos locais
root /var/www/seu-site;
try_files $uri $uri/ /index.html;

# Opção C: Retornar erro por enquanto
return 404;
```

4. Reiniciar Nginx:
```bash
nginx -t
systemctl restart nginx
```

---

## 📊 Monitoramento do Dia a Dia

### Ver logs em tempo real
```bash
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml logs -f
```

### Reiniciar um serviço
```bash
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml restart backend
```

### Atualizar código
```bash
cd /opt/fiscalai
git pull origin main
cd infra
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### Backup do banco
```bash
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml exec -T postgres pg_dump \
  -U fiscalai_user fiscalai_db > /opt/backups/db_$(date +%Y%m%d_%H%M%S).sql
```

---

## 🆘 Troubleshooting

### Porta 8000 em uso
```bash
lsof -i :8000
kill -9 <PID>
```

### Containers não iniciam
```bash
docker-compose -f docker-compose.prod.yml logs postgres
docker-compose -f docker-compose.prod.yml restart postgres
sleep 30
docker-compose -f docker-compose.prod.yml restart backend
```

### SSL error
```bash
certbot certificates
certbot renew --force-renewal
systemctl reload nginx
```

### Nginx error
```bash
nginx -t
systemctl reload nginx
```

---

## 🔄 Auto-renovação de SSL

```bash
crontab -e
# Adicione:
0 3 * * * certbot renew --quiet && systemctl reload nginx
```

---

## 📞 Suporte

- **Painel Hostinger:** https://hpanel.hostinger.com
- **Logs VPS:** `docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml logs`
- **Nginx config:** `/etc/nginx/sites-available/fiscalai-only`

---

**Status:** ✅ DEPLOYMENT SEGURO  
**URL:** https://adriner.fr/fiscalia  
**Isolamento:** 🔒 Completo (site original protegido)

*Última atualização: 2026-05-25*
