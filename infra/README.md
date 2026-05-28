# infra/ — Infraestrutura FiscalAI

Configuração Docker Compose para desenvolvimento local e produção no VPS.

## Arquivos

```
infra/
├── docker-compose.yml       # Dev local (PostgreSQL, Redis, MinIO, backend, frontend, Celery, Flower)
├── docker-compose.prod.yml  # Produção no VPS Hostinger
├── .env.prod.example        # Template de variáveis de produção
├── REFERENCE_VARS.md        # Referência completa de variáveis
├── scripts/
│   └── setup-vps.sh         # Script de setup inicial do VPS
└── README.md                # Este arquivo
```

## Dev local

```powershell
# Subir tudo
cd infra
docker compose up -d

# Parar
docker compose down

# Parar e limpar volumes
docker compose down -v
```

Portas locais:

| Serviço | URL | Credenciais |
|---|---|---|
| Frontend | http://localhost:5173 | — |
| Backend API | http://localhost:8000/docs | — |
| Flower (Celery) | http://localhost:5555 | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin_password_dev |
| PostgreSQL | localhost:5432 | fiscalai_user / fiscalai_password_dev |

## Produção

Deploy no VPS Hostinger (adriner.fr). Ver [../DEPLOYMENT_VPS.md](../DEPLOYMENT_VPS.md) para o guia completo.

```bash
# No VPS
cd /opt/fiscalai/infra
docker-compose -f docker-compose.prod.yml up -d --build
```

## Variáveis de ambiente

Ver [REFERENCE_VARS.md](REFERENCE_VARS.md) para a lista completa de variáveis e seus valores padrão.

Copiar template:
```bash
cp infra/.env.prod.example infra/.env.prod
# Editar com credenciais reais
```
