# FiscalAI — Full Stack Startup Script (Production-like environment)
# Executa: PostgreSQL, Redis, MinIO, Backend (FastAPI), Celery Worker, Flower, Frontend

param(
    [switch]$Detached = $false,
    [string]$ComposeFile = "docker-compose.prod.yml"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Iniciando FiscalAI Stack..." -ForegroundColor Cyan
Write-Host "📄 Arquivo: $ComposeFile" -ForegroundColor Gray
Write-Host ""

# Verifica se Docker está rodando
try {
    $null = docker ps
} catch {
    Write-Host "❌ Docker não está rodando. Inicie o Docker Desktop primeiro." -ForegroundColor Red
    exit 1
}

# Verifica se arquivo docker-compose existe
if (-not (Test-Path $ComposeFile)) {
    Write-Host "❌ Arquivo '$ComposeFile' não encontrado." -ForegroundColor Red
    exit 1
}

# Build das imagens (se necessário)
Write-Host "🔨 Building imagens..." -ForegroundColor Yellow
docker-compose -f $ComposeFile build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build falhou." -ForegroundColor Red
    exit 1
}

# Up da stack
Write-Host ""
Write-Host "⬆️  Subindo containers..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f $ComposeFile up -d
    Write-Host ""
    Write-Host "✅ Stack iniciada em background (detached mode)" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 URLs dos serviços:" -ForegroundColor Cyan
    Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor Green
    Write-Host "  Backend:   http://localhost:8000" -ForegroundColor Green
    Write-Host "  Flower:    http://localhost:5555" -ForegroundColor Green
    Write-Host "  MinIO:     http://localhost:9001" -ForegroundColor Green
    Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor Green
    Write-Host "  Redis:     localhost:6379" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Verificar logs:" -ForegroundColor Gray
    Write-Host "  docker-compose -f $ComposeFile logs -f backend" -ForegroundColor Gray
    Write-Host "  docker-compose -f $ComposeFile logs -f frontend" -ForegroundColor Gray
    Write-Host "  docker-compose -f $ComposeFile logs -f celery_worker" -ForegroundColor Gray
} else {
    docker-compose -f $ComposeFile up
}
