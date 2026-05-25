#!/bin/bash
# 🚀 DEPLOY RÁPIDO FISCALAI - adriner.fr/fiscalia
# Copie e cole isto na VPS (após SSH conectado)

set -e

cd /tmp && cat > deploy.sh << 'EOF'
#!/bin/bash
set -e
echo "🚀 DEPLOY FISCALAI - https://adriner.fr/fiscalia"

# 1. Docker Compose v2
apt-get update -qq && apt-get install -y -qq curl
apt-get remove -y docker-compose 2>/dev/null || true
curl -sL "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 2. Limpar
cd /opt/fiscalai/infra
docker-compose -f docker-compose.prod.yml kill 2>/dev/null || true
docker-compose -f docker-compose.prod.yml down --volumes --remove-orphans 2>/dev/null || true
docker system prune -f 2>/dev/null || true
docker rm -f fiscalai-* 2>/dev/null || true

# 3. Atualizar e build
cd /opt/fiscalai && git pull origin main
cd infra
docker-compose -f docker-compose.prod.yml build --no-cache --pull 2>&1 | tail -10

# 4. Start
docker-compose -f docker-compose.prod.yml up -d
sleep 180
docker-compose -f docker-compose.prod.yml ps

# 5. SSL
apt-get install -y -qq certbot python3-certbot-nginx
certbot certonly --standalone -d adriner.fr --non-interactive --agree-tos --email admin@adriner.fr 2>/dev/null || true

# 6. Nginx (SEGURO - /fiscalia isolado)
apt-get install -y -qq nginx

cat > /etc/nginx/sites-available/fiscalai-only <<'NGINX_EOF'
upstream backend { server localhost:8000; }
upstream frontend { server localhost:5173; }

server {
    listen 80;
    server_name adriner.fr www.adriner.fr;
    location /fiscalia { return 301 https://$server_name$request_uri; }
    location / { }
}

server {
    listen 443 ssl http2;
    server_name adriner.fr www.adriner.fr;

    ssl_certificate /etc/letsencrypt/live/adriner.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/adriner.fr/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    client_max_body_size 100M;

    location = /fiscalia { return 301 /fiscalia/; }
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
    location /fiscalia/health { proxy_pass http://backend/health; }
    location / { }
}
NGINX_EOF

rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
ln -sf /etc/nginx/sites-available/fiscalai-only /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
systemctl enable nginx

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETO!"
echo "=========================================="
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml ps
echo ""
echo "🌐 Acesse: https://adriner.fr/fiscalia"
echo "🔗 API Docs: https://adriner.fr/fiscalia/api/docs"
echo "🔗 Flower: https://adriner.fr/fiscalia/flower"
echo "🔗 MinIO: https://adriner.fr/fiscalia/minio"
echo ""
echo "📝 Seu pai configura o resto em:"
echo "   /etc/nginx/sites-available/fiscalai-only"
EOF

chmod +x deploy.sh && bash deploy.sh
