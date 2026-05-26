# FiscalAI — Full Stack Shutdown Script
# Para toda a stack e limpa volumes/containers

param(
    [switch]$Prune = $false,
    [string]$ComposeFile = "docker-compose.prod.yml"
)

$ErrorActionPreference = "Stop"

Write-Host "🛑 Parando FiscalAI Stack..." -ForegroundColor Yellow

# Down da stack
docker-compose -f $ComposeFile down

if ($Prune) {
    Write-Host "🧹 Limpando containers e imagens dangling..." -ForegroundColor Yellow
    docker system prune -f
    Write-Host "✅ Limpeza completa executada" -ForegroundColor Green
} else {
    Write-Host "✅ Stack parada" -ForegroundColor Green
    Write-Host "💡 Use: .\down.ps1 -Prune para limpar tudo" -ForegroundColor Gray
}
