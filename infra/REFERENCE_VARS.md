# Referência de Variáveis de Ambiente — FiscalAI

Copie `.env.prod.example` para `.env.prod` e preencha os valores abaixo.

## Backend — Variáveis obrigatórias

| Variável | Exemplo | Descrição |
|---|---|---|
| `SECRET_KEY` | `(gerar com secrets.token_urlsafe(64))` | Chave JWT — NUNCA commitar |
| `DEBUG` | `false` | Sempre `false` em produção |
| `DATABASE_URL` | `postgresql://fiscalai_user:SENHA@postgres:5432/fiscalai_db` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis para cache |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/1` | Celery results |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO host:port (sem http://) |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `senha_segura` | MinIO secret key |
| `MINIO_BUCKET_NAME` | `fiscalai-documents` | Nome do bucket |
| `MINIO_USE_SSL` | `false` | SSL para MinIO (true se externo) |
| `CORS_ORIGINS` | `https://adriner.fr` | Origins permitidos (vírgula para múltiplos) |

## Backend — Variáveis opcionais

| Variável | Padrão | Descrição |
|---|---|---|
| `LOG_LEVEL` | `INFO` | DEBUG em desenvolvimento |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | TTL do access token JWT |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | TTL do refresh token |
| `ANTHROPIC_API_KEY` | `""` | Narrativa IA nos relatórios PDF (opcional) |
| `BRAND_NAME` | `FiscalAI` | Nome da plataforma (white-label) |
| `BRAND_EXPERT_NAME` | `""` | Nome do especialista no rodapé do PDF |
| `BRAND_EXPERT_TITLE` | `""` | Título do especialista |
| `BRAND_WHATSAPP` | `""` | WhatsApp no CTA do PDF |
| `SMTP_HOST` | `""` | Servidor SMTP para alertas por email |
| `SMTP_PORT` | `587` | Porta SMTP |
| `SMTP_USER` | `""` | Usuário SMTP |
| `SMTP_PASSWORD` | `""` | Senha SMTP |
| `SMTP_FROM` | `alertas@fiscalai.com.br` | Remetente dos emails |
| `ALERT_EMAIL_TO` | `""` | Destinatários (vírgula para múltiplos) |

## Frontend

| Variável | Exemplo | Descrição |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Base URL da API (relativo em prod com nginx) |

## Gerar SECRET_KEY segura

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Segurança

- **NUNCA** commitar `.env.prod` no Git — está no `.gitignore`
- Rotacionar `SECRET_KEY` invalida todos os tokens ativos (usuários precisam re-logar)
- `ANTHROPIC_API_KEY` é opcional — sem ela, relatórios PDF não incluem narrativa IA
- `SMTP_*` são opcionais — sem eles, alertas por email ficam desabilitados silenciosamente
