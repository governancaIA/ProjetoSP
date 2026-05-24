<#
.SYNOPSIS
Deploy automático do FiscalAI no EasyPanel via API

.DESCRIPTION
Automatiza:
1. Git push para GitHub
2. Criar backend app no EasyPanel
3. Criar frontend app no EasyPanel
4. Configurar domains
5. Gerar SSL certificates

.EXAMPLE
.\deploy-easypanel.ps1 -APIKey "sua_chave_api"
#>

param(
    [string]$APIKey = "",
    [string]$EasyPanelURL = "https://easypanel.io",
    [string]$GitRepo = "https://github.com/seu-usuario/fiscalai.git",
    [string]$FrontendDomain = "seu-dominio.com",
    [string]$BackendDomain = "api.seu-dominio.com"
)

Write-Host ""
Write-Host "+----------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host "¦        ?? FiscalAI — Auto Deploy EasyPanel via API            ¦" -ForegroundColor Cyan
Write-Host "+----------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

if (-not $APIKey) {
    Write-Host "? Chave API não fornecida!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Use:" -ForegroundColor Yellow
    Write-Host '  .\deploy-easypanel.ps1 -APIKey "sua_chave_api" -FrontendDomain "seu-dominio.com"' -ForegroundColor Cyan
    exit 1
}

Write-Host "?? Configuração:" -ForegroundColor Yellow
Write-Host "  • API Key: ${APIKey:0:16}..." -ForegroundColor White
Write-Host "  • Frontend Domain: $FrontendDomain" -ForegroundColor White
Write-Host "  • Backend Domain: $BackendDomain" -ForegroundColor White
Write-Host ""

# Função para chamar API EasyPanel
function Invoke-EasyPanelAPI {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [hashtable]$Body = $null
    )
    
    $headers = @{
        "Authorization" = "Bearer $APIKey"
        "Content-Type" = "application/json"
    }
    
    $url = "$EasyPanelURL/api$Endpoint"
    
    try {
        if ($Body) {
            $response = Invoke-RestMethod -Uri $url -Method $Method -Headers $headers -Body ($Body | ConvertTo-Json -Depth 10)
        } else {
            $response = Invoke-RestMethod -Uri $url -Method $Method -Headers $headers
        }
        return $response
    } catch {
        Write-Host "? Erro na API: $_" -ForegroundColor Red
        return $null
    }
}

Write-Host "1?? Testando conexão com EasyPanel..." -ForegroundColor Yellow
$testConn = Invoke-EasyPanelAPI -Endpoint "/auth/me"
if ($testConn) {
    Write-Host "   ? Conectado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "   ? Falha na autenticação. Verifique a chave API." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "2?? Fazendo git commit e push..." -ForegroundColor Yellow

# Git commit
git add -A
$commitMsg = "Deploy: FiscalAI setup completo (docker, frontend, backend)"
git commit -m $commitMsg
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ? Commit feito" -ForegroundColor Green
} else {
    Write-Host "   ?? Nada para commitar" -ForegroundColor Yellow
}

git push origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ? Push para GitHub OK" -ForegroundColor Green
} else {
    Write-Host "   ? Erro ao fazer push" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "3?? Criando Backend App no EasyPanel..." -ForegroundColor Yellow

$backendApp = @{
    name = "fiscalai-backend"
    source = @{
        type = "github"
        repo = $GitRepo
        branch = "main"
    }
    dockerfile = @{
        content = ""
        location = "./backend/Dockerfile"
    }
    ports = @(
        @{
            internal = 8000
            external = 8000
        }
    )
    environment = @{
        DEBUG = "false"
        DATABASE_URL = "postgresql://postgres:cnfcnn4xbwv7eecahjly@chatwoot_bancosped:5432/sped?sslmode=disable"
        REDIS_URL = "redis://default:JIANkalu@123@chatwoot_async:6379"
        CELERY_BROKER_URL = "redis://default:JIANkalu@123@chatwoot_async:6379/0"
        CELERY_RESULT_BACKEND = "redis://default:JIANkalu@123@chatwoot_async:6379/1"
        MINIO_ENDPOINT = "chatwoot-minio.6hjchk.easypanel.host"
        MINIO_ACCESS_KEY = "admin"
        MINIO_SECRET_KEY = "password"
        MINIO_USE_SSL = "true"
        SECRET_KEY = (python -c "import secrets; print(secrets.token_urlsafe(32))" 2>$null)
        CORS_ORIGINS = "[""https://$FrontendDomain""]"
    }
}

$backendResult = Invoke-EasyPanelAPI -Endpoint "/projects/apps" -Method "POST" -Body $backendApp
if ($backendResult) {
    Write-Host "   ? Backend app criado: $($backendResult.id)" -ForegroundColor Green
    $backendAppId = $backendResult.id
} else {
    Write-Host "   ?? Erro ao criar backend app (pode já existir)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "4?? Criando Frontend App no EasyPanel..." -ForegroundColor Yellow

$frontendApp = @{
    name = "fiscalai-frontend"
    source = @{
        type = "github"
        repo = $GitRepo
        branch = "main"
    }
    dockerfile = @{
        content = ""
        location = "./frontend/Dockerfile.prod"
    }
    ports = @(
        @{
            internal = 80
            external = 80
        }
    )
    environment = @{
        VITE_API_BASE_URL = "https://$BackendDomain/api"
    }
}

$frontendResult = Invoke-EasyPanelAPI -Endpoint "/projects/apps" -Method "POST" -Body $frontendApp
if ($frontendResult) {
    Write-Host "   ? Frontend app criado: $($frontendResult.id)" -ForegroundColor Green
    $frontendAppId = $frontendResult.id
} else {
    Write-Host "   ?? Erro ao criar frontend app (pode já existir)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "5?? Configurando domínios..." -ForegroundColor Yellow

# Associar domínio ao frontend
if ($frontendAppId) {
    $frontendDomain = @{
        domain = $FrontendDomain
        ssl = $true
    }
    $domainResult = Invoke-EasyPanelAPI -Endpoint "/projects/apps/$frontendAppId/domains" -Method "POST" -Body $frontendDomain
    if ($domainResult) {
        Write-Host "   ? Domínio frontend: $FrontendDomain" -ForegroundColor Green
    }
}

# Associar domínio ao backend
if ($backendAppId) {
    $backendDomainObj = @{
        domain = $BackendDomain
        ssl = $true
    }
    $backendDomainResult = Invoke-EasyPanelAPI -Endpoint "/projects/apps/$backendAppId/domains" -Method "POST" -Body $backendDomainObj
    if ($backendDomainResult) {
        Write-Host "   ? Domínio backend: $BackendDomain" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "-" * 66
Write-Host "? DEPLOY INICIADO NO EASYPANEL!" -ForegroundColor Green
Write-Host "-" * 66
Write-Host ""

Write-Host "?? Próximas ações:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Acesse: https://easypanel.io/projects" -ForegroundColor Cyan
Write-Host "     Verifique se as apps foram criadas" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Aguarde o build completar" -ForegroundColor Cyan
Write-Host "     Build ? Runtime Logs para acompanhar" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Verifique domains:" -ForegroundColor Cyan
Write-Host "     • Frontend: https://$FrontendDomain" -ForegroundColor Gray
Write-Host "     • Backend: https://$BackendDomain/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Teste health checks:" -ForegroundColor Cyan
Write-Host "     curl https://$FrontendDomain/health" -ForegroundColor Gray
Write-Host "     curl https://$BackendDomain/health" -ForegroundColor Gray
Write-Host ""

Write-Host "-" * 66
Write-Host ""
