# 🚀 Deploy FiscalAI via SSH na Hostinger

**VPS:** genialidadecriativa.main.tld (89.116.214.246)  
**Provedor:** Hostinger KVM 2  
**Usuário:** root  
**Status:** ✅ Em atividade até 2026-06-30

---

## 🔐 PASSO 1: Conectar via SSH

### No Windows (PowerShell como Administrador)
```powershell
ssh -i $env:USERPROFILE\.ssh\id_ed25519 root@89.116.214.246
```

### No Linux / Mac
```bash
ssh -i ~/.ssh/id_ed25519 root@89.116.214.246
```

**Primeira vez:** Responda `yes` quando pedir confirmação do host

---

## ✅ PASSO 2: Verificar Ambiente da Hostinger

Após conectar, verifique o que já está instalado:

```bash
# Verificar versão do sistema
cat /etc/os-release

# Verificar se Docker está instalado
docker --version

# Verificar se Git está instalado
git --version

# Verificar se Python está instalado
python3 --version
```

**Se faltarem**, instale:

```bash
# Atualizar sistema
apt-get update && apt-get upgrade -y

# Instalar Docker
apt-get install -y docker.io docker-compose

# Instalar Git e Python
apt-get install -y git python3 python3-pip curl wget

# Iniciar Docker
systemctl start docker
systemctl enable docker
```

---

## 📂 PASSO 3: Clonar o Repositório

```bash
# Criar diretório
mkdir -p /opt
cd /opt

# Clonar repositório
git clone https://github.com/governancaIA/ProjetoSP.git fiscalai
cd fiscalai
```

---

## ⚙️ PASSO 4: Variáveis de Ambiente (Já Configuradas)

✅ **As variáveis já foram configuradas no seu repositório local!**

O arquivo `.env.production` já contém:
- ✅ `DATABASE_URL` com senha segura
- ✅ `MINIO_ROOT_PASSWORD` com senha segura
- ✅ `SECRET_KEY` com 32 caracteres aleatórios
- ✅ `CORS_ORIGINS` configurado para genialidadecriativa.main.tld
- ✅ SMTP configurado com seu email Gmail

**Você só precisa adicionar o token Gmail:**

```bash
cd infra
nano .env.production
```

Procure a linha:
```
SMTP_PASSWORD=ilxy qili bnoc bnpy
```

**O token está aqui!** ⬆️ (já foi gerado e colocado no arquivo)

Se precisar trocar, acesse https://myaccount.google.com/apppasswords e gere um novo.

**Como editar no nano:**
1. Use `Ctrl+W` para buscar `SMTP_PASSWORD`
2. Confirme que o token está lá
3. Pressione `Ctrl+X` para sair
4. Pressione `Y` para sim
5. Pressione `Enter` para salvar

---

## 🐳 PASSO 5: Build e Deploy com Docker

```bash
# Ainda no diretório /opt/fiscalai/infra

# Build das imagens (pode levar 10-15 min)
docker-compose -f docker-compose.prod.yml build

# Iniciar containers
docker-compose -f docker-compose.prod.yml up -d

# Verificar status
docker-compose -f docker-compose.prod.yml ps
```

**Output esperado:**
```
NAME                    STATUS              PORTS
fiscalai-postgres       Up 2 minutes        5432/tcp
fiscalai-redis          Up 2 minutes        6379/tcp
fiscalai-minio          Up 2 minutes        9000/tcp, 9001/tcp
fiscalai-backend        Up 1 minute         8000/tcp
fiscalai-frontend       Up 1 minute         5000/tcp
fiscalai-celery-worker  Up 1 minute         
fiscalai-celery-beat    Up 1 minute         
fiscalai-flower         Up 1 minute         5555/tcp
```

⏳ **Aguarde 2-3 minutos** para todos os containers ficarem saudáveis. O PostgreSQL precisa se inicializar.

Se algum container ficar em `Exited`, veja os logs:
```bash
docker-compose -f docker-compose.prod.yml logs backend
```

---

## 🌐 PASSO 6: Configurar Domínio e SSL

### ✅ Domínio já aponta para o VPS

Seu domínio `genialidadecriativa.main.tld` já está configurado para apontar para **89.116.214.246** no painel Hostinger.

### Gerar Certificado SSL (Let's Encrypt)

```bash
# Instalar Certbot
apt-get install -y certbot python3-certbot-nginx

# Gerar certificado (pode levar 2-3 min)
certbot certonly --standalone -d genialidadecriativa.main.tld

# Responda às perguntas:
# Email: seu@email.com
# Aceite os termos: Y
```

**Certificado será salvo em:**
```
/etc/letsencrypt/live/genialidadecriativa.main.tld/
```

---

## 🌐 PASSO 7: Instalar Nginx (Reverse Proxy)

```bash
# Instalar Nginx
apt-get install -y nginx

# Criar arquivo de configuração
cat > /etc/nginx/sites-available/fiscalai <<'EOF'
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:5173;
}

# Redirecionar HTTP para HTTPS
server {
    listen 80;
    server_name genialidadecriativa.main.tld;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name genialidadecriativa.main.tld;

    # Certificado SSL
    ssl_certificate /etc/letsencrypt/live/genialidadecriativa.main.tld/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/genialidadecriativa.main.tld/privkey.pem;

    # Melhorias de segurança
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Tamanho máximo de upload
    client_max_body_size 100M;

    # Frontend (React) - raiz
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # Flower (Celery Monitoring)
    location /flower/ {
        proxy_pass http://localhost:5555;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # MinIO Console
    location /minio/ {
        proxy_pass http://localhost:9001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Ativar configuração
ln -s /etc/nginx/sites-available/fiscalai /etc/nginx/sites-enabled/

# Testar configuração
nginx -t

# Reiniciar Nginx
systemctl restart nginx
systemctl enable nginx
```

---

## ✅ PASSO 8: Verificar Tudo Está Funcionando

```bash
# Verificar Docker containers
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml ps

# Verificar Nginx
systemctl status nginx

# Testar conectividade
curl https://genialidadecriativa.main.tld

# Ver logs do backend
docker-compose -f /opt/fiscalai/infra/docker-compose.prod.yml logs backend
```

---

## 🎉 Acessar o FiscalAI

| Serviço | URL |
|---------|-----|
| **Frontend** | https://genialidadecriativa.main.tld |
| **Backend API** | https://genialidadecriativa.main.tld/api |
| **Swagger Docs** | https://genialidadecriativa.main.tld/api/docs |
| **Flower (Celery)** | https://genialidadecriativa.main.tld/flower |
| **MinIO Console** | https://genialidadecriativa.main.tld/minio |

---

## 📊 Comandos Úteis do Dia a Dia

### Ver Logs em Tempo Real
```bash
cd /opt/fiscalai/infra

# Todos os containers
docker-compose -f docker-compose.prod.yml logs -f

# Apenas backend
docker-compose -f docker-compose.prod.yml logs -f backend

# Apenas database
docker-compose -f docker-compose.prod.yml logs -f postgres
```

### Parar/Reiniciar Serviços
```bash
cd /opt/fiscalai/infra

# Parar todos
docker-compose -f docker-compose.prod.yml down

# Reiniciar um container específico
docker-compose -f docker-compose.prod.yml restart backend

# Reiniciar todos
docker-compose -f docker-compose.prod.yml restart
```

### Atualizar Código

```bash
cd /opt/fiscalai

# Atualizar repositório
git pull origin main

# Reconstruir imagens
cd infra
docker-compose -f docker-compose.prod.yml build

# Reiniciar containers
docker-compose -f docker-compose.prod.yml up -d
```

### Backup do Banco de Dados

```bash
cd /opt/fiscalai/infra

# Backup PostgreSQL
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump \
  -U fiscalai_user fiscalai_db > /opt/backups/db_$(date +%Y%m%d_%H%M%S).sql

# Listar backups
ls -lh /opt/backups/
```

---

## 🆘 Troubleshooting

### ❌ "Docker command not found"
```bash
# Instalar Docker
apt-get install -y docker.io docker-compose
systemctl start docker
```

### ❌ "Port 8000 already in use"
```bash
# Ver o que está usando a porta
lsof -i :8000

# Parar o processo (substitua PID)
kill -9 PID
```

### ❌ "SSL certificate error"
```bash
# Verificar certificado
certbot certificates

# Renovar manualmente
certbot renew --force-renewal

# Reiniciar Nginx
systemctl restart nginx
```

### ❌ "Database connection refused"
```bash
# Verificar container postgres
docker-compose -f docker-compose.prod.yml logs postgres

# Reiniciar database
docker-compose -f docker-compose.prod.yml restart postgres

# Aguarde 30 segundos e reinicie backend
sleep 30
docker-compose -f docker-compose.prod.yml restart backend
```

### ❌ "Frontend não carrega"
```bash
# Limpar cache do navegador (Ctrl+Shift+Delete)
# Ou acessar em modo anônimo

# Verificar logs
docker-compose -f docker-compose.prod.yml logs frontend

# Reconstruir
docker-compose -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

---

## 🔄 Renovação Automática de SSL

```bash
# Criar cron job para renovação automática
crontab -e

# Adicionar esta linha:
0 3 * * * certbot renew --quiet && systemctl reload nginx
```

---

## 📈 Monitoramento

### Ver Uso de Recursos
```bash
# CPU e Memória
docker stats

# Espaço em disco
df -h

# Espaço Docker
docker system df
```

### Limpar Espaço
```bash
# Remover imagens não usadas
docker image prune -a

# Remover volumes não usados
docker volume prune

# Limpeza completa
docker system prune -a --volumes
```

---

## 🔐 Segurança - Checklist

- [ ] Alterar todas as senhas padrão em `.env.production`
- [ ] Ativar firewall UFW
- [ ] Configurar SSH com chaves (já feito)
- [ ] Desabilitar root login direto (opcional)
- [ ] Configurar backups automáticos
- [ ] Monitorar logs regularmente
- [ ] Manter sistema atualizado

### Configurar Firewall

```bash
# Instalar UFW
apt-get install -y ufw

# Abrir portas
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw default deny incoming
ufw default allow outgoing

# Ativar
ufw enable
```

---

## ✨ Próximas Fases (Opcional)

1. **Auto-deploy com GitHub Actions**
   - Push → Build → Deploy automático

2. **Monitoring com Prometheus + Grafana**
   - Métricas de performance
   - Alertas

3. **Backups Automáticos**
   - Para S3/Cloud
   - Rotação de backups

4. **CDN com Cloudflare**
   - Cache e proteção DDoS
   - Melhor performance

---

## 📞 Suporte Hostinger

Se tiver problemas:
- Painel: https://hpanel.hostinger.com
- Suporte: help.hostinger.com
- Chat: disponível no painel

---

**Sucesso no deployment!** 🚀

*Última atualização: 2026-05-25*
