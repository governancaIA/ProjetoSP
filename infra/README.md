# Infra — Infraestrutura e Deployment

Este diretório centraliza toda a configuração de infraestrutura do projeto FiscalAI.

## Estrutura

```
infra/
├── README.md                  # Este arquivo
├── docker-compose.yml         # Dev environment (local)
├── docker-compose.prod.yml    # Production environment
│
├── docker/                    # Dockerfiles para aplicações
│   ├── backend.Dockerfile     # (futuro - mover de backend/)
│   ├── frontend.Dockerfile    # (futuro - mover de frontend/)
│   └── .dockerignore
│
├── scripts/                   # Scripts de setup e deployment
│   ├── setup-easypanel.ps1    # Setup automático EasyPanel
│   └── setup-local-env.sh     # Setup local (futuro)
│
├── k8s/                       # Kubernetes manifests (futuro)
│   └── .gitkeep
│
└── terraform/                 # Infrastructure as Code (futuro)
    └── .gitkeep
```

## Desenvolvimento Local

Inicia toda a stack de desenvolvimento:

```bash
cd infra/
docker-compose up -d
```

Acesso aos serviços:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Flower (Celery):** http://localhost:5555
- **MinIO Console:** http://localhost:9001 (user: minioadmin / pass: minioadmin_password_dev)

## Produção

Para ambientes de produção, use `docker-compose.prod.yml`:

```bash
cd infra/
docker-compose -f docker-compose.prod.yml up -d
```

**Antes de usar em produção:**
1. Altere todas as senhas em `docker-compose.prod.yml`
2. Configure variáveis de ambiente apropriadas
3. Configure domínios e SSL
4. Revise a política de restart (`restart: always`)

## EasyPanel Deployment

Para deploy automático no EasyPanel:

```powershell
cd infra/scripts
.\setup-easypanel.ps1 -APIKey "sua_chave" -GitRepo "seu_repo_url"
```

Veja [setup-easypanel.ps1](scripts/setup-easypanel.ps1) para detalhes.

## Health Checks

Todos os serviços possuem healthchecks configurados:

```bash
docker-compose ps
```

Para monitorar logs:

```bash
docker-compose logs -f [service_name]
```

## Dados Persistentes

Os volumes criados são:
- `postgres_data` — Base de dados PostgreSQL
- `redis_data` — Cache Redis
- `minio_data` — Object storage MinIO

**Cuidado:** `docker-compose down` não remove volumes. Para remover:

```bash
docker-compose down -v
```

## Roadmap

- [ ] Consolidar Dockerfiles em `docker/`
- [ ] Adicionar Kubernetes manifests
- [ ] Adicionar Terraform para AWS/GCP
- [ ] Scripts de backup para volumes
- [ ] Monitoramento com Prometheus + Grafana
