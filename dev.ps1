# FiscalAI — Dev local (Windows PowerShell)
# Uso: .\dev.ps1
# Requisitos: Docker Desktop rodando, Python 3.12+, Node.js

$ROOT = $PSScriptRoot

# ── 1. Verifica/Inicia Docker ────────────────────────────────────────────────
Write-Host "`n[1/4] Verificando Docker..." -ForegroundColor Cyan
docker info *>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Docker Desktop nao esta rodando. Tentando iniciar..." -ForegroundColor Yellow
    $dockerDesktop = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Programs\Docker\Docker\Docker Desktop.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $dockerDesktop) {
        Write-Host "ERRO: Docker Desktop nao encontrado. Instale em https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
        exit 1
    }

    Start-Process $dockerDesktop
    Write-Host "  Aguardando Docker inicializar (pode levar ~30s)..." -ForegroundColor Gray
    $timeout = 60
    $elapsed = 0
    do {
        Start-Sleep -Seconds 3
        $elapsed += 3
        docker info *>$null
        if ($LASTEXITCODE -eq 0) { break }
        Write-Host "  ... $elapsed`s" -ForegroundColor DarkGray
    } while ($elapsed -lt $timeout)

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERRO: Docker nao respondeu em ${timeout}s. Abra o Docker Desktop manualmente e tente novamente." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Docker pronto!" -ForegroundColor Green
}

# ── 2. Sobe infra (postgres + redis + minio) ──────────────────────────────────
Write-Host "[2/4] Subindo infra (postgres, redis, minio)..." -ForegroundColor Cyan
Set-Location "$ROOT\infra"
docker compose up -d postgres redis minio
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Falha ao subir infra via Docker Compose." -ForegroundColor Red
    exit 1
}

Write-Host "Aguardando servicos ficarem healthy..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# ── 3. Backend ────────────────────────────────────────────────────────────────
Write-Host "[3/4] Iniciando backend FastAPI em http://localhost:8000 ..." -ForegroundColor Cyan
Set-Location "$ROOT\backend"

# Cria venv se nao existir
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "  Criando venv Python..." -ForegroundColor Gray
    python -m venv venv
}

# Instala dependencias se necessario
$pipCheck = & venv\Scripts\pip.exe show fastapi 2>$null
if (-not $pipCheck) {
    Write-Host "  Instalando dependencias Python..." -ForegroundColor Gray
    & venv\Scripts\pip.exe install -r requirements.txt --quiet
}

# Cria .env se nao existir
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  .env criado a partir de .env.example" -ForegroundColor Yellow
}

$backendJob = Start-Process -FilePath "venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory "$ROOT\backend" `
    -PassThru -WindowStyle Normal

Write-Host "  Backend PID: $($backendJob.Id)" -ForegroundColor Gray

# ── 4. Frontend ───────────────────────────────────────────────────────────────
Write-Host "[4/4] Iniciando frontend React em http://localhost:5173 ..." -ForegroundColor Cyan
Set-Location "$ROOT\frontend"

if (-not (Test-Path "node_modules")) {
    Write-Host "  Instalando dependencias npm..." -ForegroundColor Gray
    npm install --silent
}

$frontendJob = Start-Process -FilePath "npm" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory "$ROOT\frontend" `
    -PassThru -WindowStyle Normal

Write-Host "  Frontend PID: $($frontendJob.Id)" -ForegroundColor Gray

# ── Resumo ────────────────────────────────────────────────────────────────────
Write-Host "`n========================================" -ForegroundColor Green
Write-Host " FiscalAI rodando localmente!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host " Frontend  : http://localhost:5173"
Write-Host " Backend   : http://localhost:8000"
Write-Host " API Docs  : http://localhost:8000/docs"
Write-Host " MinIO UI  : http://localhost:9001  (minioadmin / minioadmin_password_dev)"
Write-Host ""
Write-Host "Para parar tudo: feche as janelas abertas ou rode .\stop.ps1" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Green

# Salva PIDs para o stop.ps1 poder matar
@{ BackendPID = $backendJob.Id; FrontendPID = $frontendJob.Id } |
    ConvertTo-Json | Out-File "$ROOT\.dev-pids.json" -Encoding utf8
