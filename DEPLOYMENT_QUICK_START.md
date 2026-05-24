# ?? FiscalAI — Deploy Rápido no VPS Hostinger

> **TL;DR:** 4 passos para colocar FiscalAI em produção

---

## ? 4 Passos Rápidos

### Passo 1??: SSH no VPS

```bash
ssh -i sua_chave.pem root@seu_vps_ip
```

### Passo 2??: Instalar Docker + Clonar Repo

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh

# Clonar repositório
git clone https://github.com/seu-usuario/fiscalai.git /var/www/fiscalai
cd /var/www/fiscalai
```

### Passo 3??: Configurar Environment

```bash
# Copiar template
cp .env.example .env

# Editar com suas credenciais
nano .env
```

**Principais mudanças:**

```env
# Suas credenciais reais
DATABASE_URL=postgresql://postgres:senha@chatwoot_bancosped:5432/sped?sslmode=disable
REDIS_URL=redis://default:senha@chatwoot_async:6379
MINIO_ENDPOINT=chatwoot-minio.6hjchk.easypanel.host
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password

# Segurança
DEBUG=false
SECRET_KEY=cole-uma-chave-aleatoria-aqui

# Seu domínio
CORS_ORIGINS=["https://seu-dominio.com"]
```

### Passo 4??: Iniciar Stack

```bash
# Iniciar
docker-compose -f docker-compose.prod.yml up -d

# Verificar
docker-compose ps

# Ver logs
docker-compose logs -f backend
```

---

## ?? Configurar nginx + SSL (Opcional, mas recomendado)

### Instalar nginx

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### Copiar configuração do guia DEPLOYMENT_VPS.md

```bash
sudo nano /etc/nginx/sites-available/fiscalai
# Copiar config de DEPLOYMENT_VPS.md ? "Reverse Proxy (nginx)"
```

### Gerar certificado SSL

```bash
sudo certbot certonly --nginx -d seu-dominio.com -d www.seu-dominio.com
```

### Ativar

```bash
sudo ln -s /etc/nginx/sites-available/fiscalai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## ? Validar Deployment

### API respondendo?

```bash
curl https://seu-dominio.com/health
# Esperado: {"status":"healthy","service":"FiscalAI API"}
```

### Frontend carregando?

```bash
curl https://seu-dominio.com/ | head -20
# Esperado: HTML do React
```

### Containers rodando?

```bash
docker-compose ps
# Status: Up
```

### Logs OK?

```bash
docker-compose logs backend | grep "Application startup complete"
```

---

## ?? Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| `Connection refused` | Aguarde 30s para containers iniciarem |
| `Database error` | Verificar `DATABASE_URL` em `.env` |
| `Redis error` | Verificar `REDIS_URL` em `.env` |
| `SSL error` | Certbot não rodou? Executar manualmente |
| `nginx 502` | Backend não está respondendo? Ver logs |

---

## ?? Acessar Aplicação

```
Frontend: https://seu-dominio.com
API: https://seu-dominio.com/api
API Docs: https://seu-dominio.com/api/docs
Flower: https://seu-dominio.com/flower (opcional)
MinIO: https://minio-console-url (direto, não via nginx)
```

---

## ?? Checklist Final

- [ ] SSH no VPS ?
- [ ] Docker instalado ?
- [ ] Repo clonado ?
- [ ] `.env` configurado ?
- [ ] `docker-compose up` rodando ?
- [ ] nginx configurado (opcional) ?
- [ ] Certificado SSL ?
- [ ] `curl /health` respondendo ?
- [ ] Frontend acessível ?

---

## ?? Pronto!

Você está em produção!

Para detalhes adicionais, veja [DEPLOYMENT_VPS.md](./DEPLOYMENT_VPS.md).
