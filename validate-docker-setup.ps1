<#
.SYNOPSIS
Valida se o ambiente Docker está configurado corretamente para FiscalAI

.DESCRIPTION
Verifica:
- Docker está instalado
- Docker Compose está disponível
- Portas necessárias estão livres
- Variáveis de ambiente estão configuradas
#>

Write-Host "?? Validando setup Docker para FiscalAI..." -ForegroundColor Cyan
Write-Host ""

$errors = @()
$warnings = @()
$success = @()

# 1. Verificar Docker
Write-Host "1?? Verificando Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    if ($dockerVersion) {
        Write-Host "   ? Docker: $dockerVersion" -ForegroundColor Green
        $success += "Docker installed"
    }
}
catch {
    $errors += "Docker não está instalado. Instale em: https://www.docker.com/products/docker-desktop"
}

# 2. Verificar Docker Compose
Write-Host "2?? Verificando Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version
    if ($composeVersion) {
        Write-Host "   ? Docker Compose: $composeVersion" -ForegroundColor Green
        $success += "Docker Compose installed"
    }
}
catch {
    $errors += "Docker Compose não está instalado"
}

# 3. Verificar portas
Write-Host "3?? Verificando disponibilidade de portas..." -ForegroundColor Yellow

$ports = @{
    "5173" = "Frontend"
    "8000" = "Backend API"
    "5432" = "PostgreSQL"
    "6379" = "Redis"
    "9000" = "MinIO"
    "9001" = "MinIO Console"
    "5555" = "Flower"
}

foreach ($port in $ports.GetEnumerator()) {
    $portNum = $port.Key
    $service = $port.Value
    
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $portNum)
        $listener.Start()
        $listener.Stop()
        Write-Host "   ? Porta $portNum ($service) disponível" -ForegroundColor Green
        $success += "Port $portNum available"
    }
    catch {
        $warnings += "?? Porta $portNum ($service) pode estar em uso"
        Write-Host "   ?? Porta $portNum ($service) pode estar ocupada" -ForegroundColor Yellow
    }
}

# 4. Verificar .env
Write-Host "4?? Verificando configuração..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "   ? Arquivo .env existe" -ForegroundColor Green
    $success += ".env file exists"
}
else {
    if (Test-Path ".env.example") {
        Write-Host "   ?? .env não encontrado, mas .env.example existe" -ForegroundColor Cyan
        Write-Host "      Execute: copy .env.example .env" -ForegroundColor Cyan
        $warnings += "Missing .env file (can be copied from .env.example)"
    }
    else {
        $errors += ".env e .env.example não encontrados"
    }
}

# 5. Verificar docker-compose.yml
Write-Host "5?? Verificando docker-compose.yml..." -ForegroundColor Yellow
if (Test-Path "docker-compose.yml") {
    Write-Host "   ? docker-compose.yml existe" -ForegroundColor Green
    $success += "docker-compose.yml exists"
}
else {
    $errors += "docker-compose.yml não encontrado no diretório raiz"
}

# 6. Verificar Dockerfiles
Write-Host "6?? Verificando Dockerfiles..." -ForegroundColor Yellow
if (Test-Path "backend\Dockerfile") {
    Write-Host "   ? backend/Dockerfile existe" -ForegroundColor Green
    $success += "backend Dockerfile exists"
}
else {
    $errors += "backend/Dockerfile não encontrado"
}

if (Test-Path "frontend\Dockerfile") {
    Write-Host "   ? frontend/Dockerfile existe" -ForegroundColor Green
    $success += "frontend Dockerfile exists"
}
else {
    $errors += "frontend/Dockerfile não encontrado"
}

Write-Host ""
Write-Host "-" * 60

# Resumo
Write-Host "?? Resultado da Validação:" -ForegroundColor Cyan
Write-Host ""

if ($errors.Count -gt 0) {
    Write-Host "? Erros encontrados:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "   • $error" -ForegroundColor Red
    }
    Write-Host ""
}

if ($warnings.Count -gt 0) {
    Write-Host "?? Avisos:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "   • $warning" -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host "? Verificações Bem-Sucedidas: $($success.Count)" -ForegroundColor Green
Write-Host ""

if ($errors.Count -eq 0) {
    Write-Host "?? Setup Docker validado com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Próximos passos:" -ForegroundColor Cyan
    Write-Host "   1. copy .env.example .env (se não tiver .env)" -ForegroundColor Cyan
    Write-Host "   2. docker-compose up --build" -ForegroundColor Cyan
    Write-Host "   3. Acessar http://localhost:5173" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}
else {
    Write-Host "?? Configure os erros acima antes de prosseguir." -ForegroundColor Red
    exit 1
}
