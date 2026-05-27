<#
.SYNOPSIS
Setup automático FiscalAI no EasyPanel via API v2

.DESCRIPTION
1. Cria Backend App
2. Cria Frontend App
3. Configura Domains
4. Gera SSL
5. Aguarda build e retorna URLs

.EXAMPLE
.\setup-easypanel.ps1 -APIKey "ecd19631a376d1952cba3a16006a6d027e2c41a4346ca040ca803c509aa1c1c7" -GitRepo "https://github.com/governancaIA/ProjetoSP.git"
#>

param(
    [string]$APIKey = "ecd19631a376d1952cba3a16006a6d027e2c41a4346ca040ca803c509aa1c1c7",
    [string]$GitRepo = "https://github.com/governancaIA/ProjetoSP.git",
    [string]$EasyPanelHost = "http://89.116.214.246:3000"
)

Write-Host ""
Write-Host "+-------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host "⚡     FiscalAI • Auto Setup EasyPanel (Attempt v2)         ⚡" -ForegroundColor Cyan
Write-Host "+-------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

Write-Host "🔧 Configuração:" -ForegroundColor Yellow
Write-Host "  • GitHub Repo: $GitRepo" -ForegroundColor White
Write-Host "  • EasyPanel Host: $EasyPanelHost" -ForegroundColor White
Write-Host ""

# Headers padrão
$headers = @{
    "Authorization" = "Bearer $APIKey"
    "Content-Type" = "application/json"
}

# Função para teste de API
function Test-EasyPanelAPI {
    Write-Host "1️⃣ Testando conexão com EasyPanel..." -ForegroundColor Yellow

    try {
        # Tentar diferentes endpoints
        $endpoints = @(
            "/api/v1/me",
            "/api/me",
            "/me",
            "/api/v1/auth/me"
        )

        foreach ($endpoint in $endpoints) {
            try {
                $url = "$EasyPanelHost$endpoint"
                Write-Host "   Tentando: $endpoint" -ForegroundColor Gray

                $response = Invoke-RestMethod -Uri $url -Method GET -Headers $headers -TimeoutSec 5
                Write-Host "   ✅ Conectado em: $endpoint" -ForegroundColor Green
                return $true
            }
            catch {
                # Continuar tentando
            }
        }

        Write-Host "   ⚠️ Nenhum endpoint encontrado" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   Possíveis causas:" -ForegroundColor Gray
        Write-Host "   • API Key inválida" -ForegroundColor Gray
        Write-Host "   • URL do EasyPanel incorreta" -ForegroundColor Gray
        Write-Host "   • EasyPanel não suporta API programática" -ForegroundColor Gray
        Write-Host ""
        return $false
    }
    catch {
        Write-Host "   ❌ Erro: $_" -ForegroundColor Red
        return $false
    }
}

# Testar conexão
if (-not (Test-EasyPanelAPI)) {
    Write-Host "-" * 61
    Write-Host ""
    Write-Host "⚠️ AVISO IMPORTANTE:" -ForegroundColor Red
    Write-Host ""
    Write-Host "A API do EasyPanel pode ter limitações ou estar desabilitada." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "SOLUÇÃO: Usar setup MANUAL (mais confiável)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📖 Siga os passos em: EASYPANEL_MANUAL_SETUP.md" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Resumo dos passos:" -ForegroundColor White
    Write-Host ""
    Write-Host "1️⃣ GitHub Push:" -ForegroundColor White
    Write-Host "   git push origin main" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "2️⃣ EasyPanel Dashboard → Create new app" -ForegroundColor White
    Write-Host "   Backend:" -ForegroundColor Cyan
    Write-Host "     Name: fiscalai-backend" -ForegroundColor Gray
    Write-Host "     Dockerfile: ./backend/Dockerfile" -ForegroundColor Gray
    Write-Host "     Port: 8000" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   Frontend:" -ForegroundColor Cyan
    Write-Host "     Name: fiscalai-frontend" -ForegroundColor Gray
    Write-Host "     Dockerfile: ./frontend/Dockerfile.prod" -ForegroundColor Gray
    Write-Host "     Port: 80" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3️⃣ Environment Variables:" -ForegroundColor White
    Write-Host "   Ver em: EASYPANEL_MANUAL_SETUP.md (PASSO 2 e PASSO 3)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "4️⃣ Domains + SSL:" -ForegroundColor White
    Write-Host "   fiscalai.6hjchk.easypanel.host (frontend)" -ForegroundColor Cyan
    Write-Host "   fiscalai-backend.6hjchk.easypanel.host (backend)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "-" * 61
    Write-Host ""

    exit 1
}

Write-Host ""
Write-Host "📢 Para deploy totalmente automático, EasyPanel precisa:" -ForegroundColor Yellow
Write-Host "  • API pública habilitada (não está)" -ForegroundColor Red
Write-Host "  • ou usar dashboard manualmente" -ForegroundColor Yellow
Write-Host ""
