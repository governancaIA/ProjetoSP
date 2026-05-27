#!/bin/bash
# ============================================================
#  FiscalAI — Setup Inicial da VPS (Ubuntu / Hostinger)
#  Execute como root: bash setup-vps.sh
# ============================================================
set -e

REPO_URL="https://github.com/governancaIA/ProjetoSP.git"
APP_DIR="/opt/fiscalai"
DEPLOY_USER="deploy-fiscalai"

echo "========================================"
echo "  FiscalAI — Setup VPS"
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
if [ -d "$APP_DIR/.git" ]; then
    echo "Repositório já existe. Fazendo git pull..."
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
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
    echo ""
else
    echo "Chave SSH já existe em $SSH_KEY_PATH"
fi

# ---- 7. Criar .env.prod ----
echo ""
echo "[7/7] Criando arquivo .env.prod..."
ENV_FILE="$APP_DIR/infra/.env.prod"

if [ -f "$ENV_FILE" ]; then
    echo ".env.prod já existe — não sobrescrevendo."
else
    cp "$APP_DIR/infra/.env.prod.example" "$ENV_FILE"
    echo ""
    echo "============================================================"
    echo "  AÇÃO NECESSÁRIA: preencha o arquivo .env.prod"
    echo "  nano $ENV_FILE"
    echo "============================================================"
fi

# ---- Resumo ----
echo ""
echo "========================================"
echo "  Setup concluído!"
echo "========================================"
echo ""
echo "Próximos passos:"
echo ""
echo "  1. Preencha os secrets no GitHub Actions:"
echo "     SSH_HOST  = 89.116.214.246"
echo "     SSH_USER  = root"
echo "     SSH_PRIVATE_KEY = (conteúdo impresso acima)"
echo ""
echo "  2. Edite o .env.prod:"
echo "     nano $ENV_FILE"
echo ""
echo "  3. Suba a stack manualmente pela primeira vez:"
echo "     cd $APP_DIR/infra"
echo "     docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "  4. Verifique:"
echo "     curl http://89.116.214.246/health"
echo ""
echo "  Depois disso, cada push na main fará deploy automático."
