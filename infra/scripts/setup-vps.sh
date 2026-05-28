#!/bin/bash
# ============================================================
#  FiscalAI — Setup Inicial da VPS (Ubuntu)
#  Execute como root: bash setup-vps.sh
#  Gera .env.prod com senhas aleatórias — sem edição manual.
# ============================================================
set -e

REPO_URL="https://github.com/governancaIA/ProjetoSP.git"
APP_DIR="/opt/fiscalai/ProjetoSP"

VPS_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo "========================================"
echo "  FiscalAI — Setup VPS"
echo "  IP: $VPS_IP"
echo "========================================"

# ---- 1. Atualizar sistema ----
echo ""
echo "[1/7] Atualizando pacotes do sistema..."
apt-get update -qq && apt-get upgrade -y -qq

# ---- 2. Instalar Docker ----
echo ""
echo "[2/7] Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    echo "Docker instalado com sucesso."
else
    echo "Docker já instalado: $(docker --version)"
fi

# ---- 3. Instalar utilitários ----
echo ""
echo "[3/7] Instalando utilitários (git, curl, ufw)..."
apt-get install -y -qq git curl ufw

# ---- 4. Configurar firewall ----
echo ""
echo "[4/7] Configurando firewall (UFW)..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "Firewall configurado: SSH + 80 + 443 liberados."

# ---- 5. Clonar o repositório ----
echo ""
echo "[5/7] Clonando repositório em $APP_DIR..."
mkdir -p /opt/fiscalai
if [ -d "$APP_DIR/.git" ]; then
    echo "Repositório já existe. Fazendo git pull..."
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# ---- 6. Criar chave SSH para GitHub Actions ----
echo ""
echo "[6/7] Gerando chave SSH para deploy automatizado..."
SSH_KEY_PATH="/root/.ssh/fiscalai_deploy"

if [ ! -f "$SSH_KEY_PATH" ]; then
    ssh-keygen -t ed25519 -C "fiscalai-deploy@vps" -f "$SSH_KEY_PATH" -N ""
    cat "$SSH_KEY_PATH.pub" >> /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    echo ""
    echo "============================================================"
    echo "  CHAVE PRIVADA — adicione como secret SSH_PRIVATE_KEY"
    echo "  no GitHub: Settings > Secrets > Actions"
    echo "============================================================"
    cat "$SSH_KEY_PATH"
    echo "============================================================"
else
    echo "Chave SSH já existe em $SSH_KEY_PATH"
fi

# ---- 7. Gerar .env.prod automaticamente ----
echo ""
echo "[7/7] Gerando .env.prod com senhas aleatórias..."
ENV_FILE="$APP_DIR/infra/.env.prod"

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
MINIO_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

cat > "$ENV_FILE" <<EOF
# Gerado automaticamente por setup-vps.sh em $(date)
# NÃO commite este arquivo no git.

ENV=production
DEBUG=False
LOG_LEVEL=INFO
SECRET_KEY=${SECRET_KEY}

DOMAIN=${VPS_IP}
ALLOWED_HOSTS=${VPS_IP}
CORS_ORIGINS=http://${VPS_IP}

POSTGRES_USER=fiscalai_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=fiscalai_db
DATABASE_URL=postgresql://fiscalai_user:${POSTGRES_PASSWORD}@postgres:5432/fiscalai_db

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

MINIO_ENDPOINT=minio:9000
MINIO_ROOT_USER=fiscalai_minio_admin
MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
MINIO_BUCKET=fiscalai-documents
MINIO_BROWSER_REDIRECT_URL=http://${VPS_IP}:9001
EOF

echo "    .env.prod criado com sucesso."
echo ""
echo "    POSTGRES_PASSWORD : ${POSTGRES_PASSWORD}"
echo "    MINIO_PASSWORD    : ${MINIO_PASSWORD}"
echo "    (guarde em local seguro!)"

# ---- Corrigir compose: remover version obsoleto ----
COMPOSE_FILE="$APP_DIR/infra/docker-compose.prod.yml"
if grep -q "^version:" "$COMPOSE_FILE" 2>/dev/null; then
    sed -i '/^version:/d' "$COMPOSE_FILE"
    echo ""
    echo "    Linha 'version' obsoleta removida do docker-compose.prod.yml"
fi

# ---- Subir a stack ----
echo ""
echo "========================================"
echo "  Subindo containers..."
echo "========================================"
cd "$APP_DIR/infra"
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

echo ""
echo "Aguardando banco de dados..."
sleep 15

echo ""
echo "Rodando migrations..."
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

echo ""
echo "Status dos containers:"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "========================================"
echo "  Deploy concluído!"
echo "  Acesse: http://${VPS_IP}"
echo ""
echo "  Para CI/CD automático, adicione no GitHub"
echo "  Settings > Secrets > Actions:"
echo "    SSH_HOST        = ${VPS_IP}"
echo "    SSH_USER        = root"
echo "    SSH_PRIVATE_KEY = (impresso acima no passo 6)"
echo "========================================"
