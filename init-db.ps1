# FiscalAI — Database Initialization Script
# Executa: Alembic migrations, cria schema de tenant de exemplo

param(
    [string]$TenantId = "example-tenant-001"
)

$ErrorActionPreference = "Stop"

Write-Host "🗄️  Inicializando banco de dados..." -ForegroundColor Cyan
Write-Host ""

# Aguarda PostgreSQL estar saudável
Write-Host "⏳ Aguardando PostgreSQL..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U fiscalai_user -d fiscalai_db 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ PostgreSQL está pronto" -ForegroundColor Green
            break
        }
    } catch {
        # Container pode não estar pronto ainda
    }
    $attempt++
    Start-Sleep -Seconds 1
    if ($attempt -eq $maxAttempts) {
        Write-Host "❌ PostgreSQL não ficou pronto a tempo" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🔄 Executando Alembic migrations..." -ForegroundColor Yellow
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Migrations falharam" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Migrations executadas com sucesso" -ForegroundColor Green
Write-Host ""
Write-Host "🏢 Criando schema de tenant de exemplo..." -ForegroundColor Yellow
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.core.database import create_tenant_schema
create_tenant_schema('$TenantId')
print(f'✅ Schema tenant_$TenantId criado')
"

Write-Host ""
Write-Host "🎉 Banco de dados inicializado!" -ForegroundColor Green
