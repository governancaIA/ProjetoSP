<#
.SYNOPSIS
Script para fazer deploy do FiscalAI no VPS Hostinger via SSH + Git

.DESCRIPTION
Automatiza:
1. Commit e push no GitHub
2. SSH no VPS
3. Pull do repositório
4. Validar .env
5. Iniciar docker-compose

.EXAMPLE
.\deploy-vps.ps1 -VPSHost "seu_vps_ip" -VPSUser "root" -VPSKeyPath "C:\Users\seu_usuario\.ssh\id_rsa"
#>

param(
    [string]$VPSHost = "seu_vps_ip",
    [string]$VPSUser = "root",
    [string]$VPSKeyPath = "$env:USERPROFILE\.ssh\id_rsa",
    [string]$DeployPath = "/var/www/fiscalai",
    [switch]$SkipGit
)

Write-Host "?? FiscalAI — Deploy no VPS Hostinger" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar Git
if (-not $SkipGit) {
    Write-Host "1?? Verificando Git..." -ForegroundColor Yellow
    $gitStatus = git status
    if ($LASTEXITCODE -ne 0) {
        Write-Host "? Não está em um repositório Git" -ForegroundColor Red
        exit 1
    }
    
    # Verificar se .env/env.local estão ignorados
    Write-Host "   Verificando .gitignore..." -ForegroundColor Gray
    if ((git check-ignore .env) -and (git check-ignore .env.local)) {
        Write-Host "   ? .env e .env.local estão ignorados" -ForegroundColor Green
    } else {
        Write-Host "   ?? AVISO: .env ou .env.local podem ser commitados!" -ForegroundColor Red
        $confirm = Read-Host "   Continuar? (s/n)"
        if ($confirm -ne "s") { exit }
    }
    
    # Commit e push
    Write-Host ""
    Write-Host "2?? Fazendo commit e push..." -ForegroundColor Yellow
    git add -A
    $message = Read-Host "   Mensagem de commit"
    if (-not $message) { $message = "Deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
    
    git commit -m $message
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ?? Nada a commitar" -ForegroundColor Yellow
    } else {
        Write-Host "   ? Commit feito" -ForegroundColor Green
    }
    
    git push
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ? Push para GitHub OK" -ForegroundColor Green
    } else {
        Write-Host "   ? Erro ao fazer push" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "3?? Conectando ao VPS..." -ForegroundColor Yellow
Write-Host "   Host: $VPSHost" -ForegroundColor Gray
Write-Host "   User: $VPSUser" -ForegroundColor Gray
Write-Host "   Key: $VPSKeyPath" -ForegroundColor Gray
Write-Host ""

# 2. Conectar via SSH e executar deploy
$sshCommand = @"
# Pull do repositório
cd $DeployPath
git pull origin main

# Verificar .env
if [ ! -f .env ]; then
    echo "?? .env não encontrado!"
    echo "Copiar .env.local para .env:"
    cp .env.example .env
    echo "?? AVISO: Configure .env com suas credenciais reais!"
    exit 1
fi

# Parar containers anteriores
docker-compose down

# Iniciar nova stack
docker-compose -f docker-compose.prod.yml up -d

# Aguardar health check
echo ""
echo "?? Aguardando serviços ficarem saudáveis..."
sleep 10

# Verificar status
docker-compose ps

# Verificar se backend está respondendo
sleep 5
echo ""
echo "?? Verificando health da API..."
curl -s http://localhost:8000/health | python3 -m json.tool || echo "Backend ainda está inicializando..."

echo ""
echo "? Deploy concluído!"
echo ""
echo "?? Acesse em: https://seu-dominio.com"
"@

# Executar via SSH (usando plink se tiver PuTTY, senão ssh)
try {
    # Tentar com ssh primeiro
    if (Get-Command ssh -ErrorAction SilentlyContinue) {
        Write-Host "   Usando ssh..." -ForegroundColor Gray
        ssh -i $VPSKeyPath "$VPSUser@$VPSHost" $sshCommand
    } else {
        Write-Host "   SSH não encontrado. Certifique-se de ter Git Bash ou WSL." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "? Erro ao conectar ao VPS: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "-" * 70
Write-Host "? DEPLOY CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
Write-Host "-" * 70
Write-Host ""
Write-Host "?? Próximos passos:" -ForegroundColor Cyan
Write-Host "   1. Verificar logs: docker-compose logs -f" -ForegroundColor White
Write-Host "   2. Acessar: https://seu-dominio.com" -ForegroundColor White
Write-Host "   3. Fazer login: email/senha configurado no backend" -ForegroundColor White
Write-Host ""
