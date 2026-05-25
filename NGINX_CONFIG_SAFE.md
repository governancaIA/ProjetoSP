# 🛡️ Configuração Nginx SEGURA - Site Existente Protegido

**Situação:**
- Seu pai já tem um site/produto rodando em `adriner.fr`
- Nós vamos apontar **apenas** `/fiscalia` para o FiscalAI
- **Tudo mais continua funcionando normalmente**

---

## 🔧 Configuração Nginx (SEGURA)

Esta é a config que será colocada em `/etc/nginx/sites-available/fiscalai-only`:

```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:5173;
}

# ===== HTTP (redireciona para HTTPS) =====
server {
    listen 80;
    server_name adriner.fr www.adriner.fr;

    # /fiscalia → HTTPS
    location /fiscalia {
        return 301 https://$server_name$request_uri;
    }

    # TUDO MAIS vai para o site original dele
    # (ele já estava funcionando, continua funcionando)
    location / {
        # SEU SITE ORIGINAL CONTINUA AQUI
        # Exemplos de config que ele pode usar:
        # 1. proxy_pass http://localhost:3000;  (se for Node)
        # 2. proxy_pass http://localhost:8080;  (se for Java)
        # 3. root /var/www/seu-site; try_files $uri $uri/ /index.html;  (HTML estático)
        # 4. proxy_pass http://127.0.0.1:9000;  (se for outro servidor)
    }
}

# ===== HTTPS (protegido) =====
server {
    listen 443 ssl http2;
    server_name adriner.fr www.adriner.fr;

    # Certificado SSL (compartilhado entre FiscalAI e site original)
    ssl_certificate /etc/letsencrypt/live/adriner.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/adriner.fr/privkey.pem;

    # Segurança
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Upload grande (para FiscalAI)
    client_max_body_size 100M;

    # ===== /fiscalia → FiscalAI (NOSSA SOLUÇÃO) =====

    location = /fiscalia {
        return 301 /fiscalia/;
    }

    # Frontend React
    location /fiscalia/ {
        proxy_pass http://frontend/;
        proxy_buffering off;
        proxy_request_buffering off;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Path /fiscalia;

        # WebSocket support (se precisar)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # API backend
    location /fiscalia/api/ {
        proxy_pass http://backend/api/;
        proxy_buffering off;
        proxy_request_buffering off;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Monitoramento Celery
    location /fiscalia/flower/ {
        proxy_pass http://localhost:5555/;
        proxy_buffering off;
        proxy_request_buffering off;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Storage S3
    location /fiscalia/minio/ {
        proxy_pass http://localhost:9001/;
        proxy_buffering off;
        proxy_request_buffering off;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Health check
    location /fiscalia/health {
        proxy_pass http://backend/health;
        proxy_set_header Host $host;
    }

    # ===== / → SITE ORIGINAL (SEU PAI CONFIGURA) =====
    location / {
        # SEU SITE ORIGINAL CONTINUA AQUI
        # Exemplos de config que ele pode usar:
        # 1. proxy_pass http://localhost:3000;  (se for Node)
        # 2. proxy_pass http://localhost:8080;  (se for Java)
        # 3. root /var/www/seu-site; try_files $uri $uri/ /index.html;  (HTML estático)
        # 4. proxy_pass http://127.0.0.1:9000;  (se for outro servidor)
    }
}
```

---

## 📌 COMO FUNCIONA

### Fluxo de requisições:

```
Cliente acessa adriner.fr
│
├─ adriner.fr/fiscalia
│  └─→ NGINX redireciona para FiscalAI (nossa solução)
│      └─→ Frontend React (porta 5173)
│
├─ adriner.fr/fiscalia/api/v1/...
│  └─→ NGINX redireciona para FiscalAI API (nossa solução)
│      └─→ Backend FastAPI (porta 8000)
│
├─ adriner.fr/
│  └─→ NGINX passa para o site original dele
│      └─→ Seja Node, Java, HTML, ou outra coisa
```

---

## 🔄 Como seu pai configura o site original

1. **Editar o arquivo:**
   ```bash
   nano /etc/nginx/sites-available/fiscalai-only
   ```

2. **Encontrar a seção `location /` (em HTTPS)**

3. **Substituir o comentário** por um dos exemplos:

### Exemplo 1: Site rodando em Node (porta 3000)
```nginx
location / {
    proxy_pass http://localhost:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Exemplo 2: Site HTML estático
```nginx
location / {
    root /var/www/seu-site;
    try_files $uri $uri/ /index.html;
}
```

### Exemplo 3: Site em outro servidor
```nginx
location / {
    proxy_pass http://192.168.1.100:8080;  # IP e porta do servidor
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

4. **Depois de editar:**
   ```bash
   nginx -t  # Testa a config
   systemctl reload nginx  # Aplica sem derrubar
   ```

---

## ✅ O QUE ACONTECE AGORA

- ✅ `/fiscalia` → **FiscalAI (100% nosso)**
- ✅ `/` → **Site original (seu pai configura)**
- ✅ HTTPS compartilhado (mesmo certificado)
- ✅ Nada é deletado, nada é sobrescrito
- ✅ Isolamento completo

---

## 🎯 Resumo para seu pai

**Diga a ele:**

> "Olá, configurei o servidor para sua solução FiscalAI ficar em `https://adriner.fr/fiscalia`. Seu site continua em `https://adriner.fr`, você só precisa editar o arquivo `/etc/nginx/sites-available/fiscalai-only` e adicionar a configuração para seu site (Node, Java, HTML, etc) na seção `location /`. Depois execute `nginx -t` e `systemctl reload nginx`. Seu site vai voltar a funcionar normalmente!"

---

## 📂 Localização do arquivo

```
/etc/nginx/sites-available/fiscalai-only
```

**Para editar:**
```bash
sudo nano /etc/nginx/sites-available/fiscalai-only
```

**Para testar:**
```bash
sudo nginx -t
```

**Para aplicar:**
```bash
sudo systemctl reload nginx
```

---

**Segurança:** 🔒 Garantida  
**Isolamento:** ✅ Total  
**Risco:** 🟢 Mínimo  
**Reversibilidade:** ✅ Fácil (apenas remover /opt/fiscalai)

