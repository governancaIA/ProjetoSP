# FiscalAI — Para todos os servicos dev
$ROOT = $PSScriptRoot
$pidsFile = "$ROOT\.dev-pids.json"

if (Test-Path $pidsFile) {
    $pids = Get-Content $pidsFile | ConvertFrom-Json
    foreach ($pid in @($pids.BackendPID, $pids.FrontendPID)) {
        if ($pid -and (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $pid -Force
            Write-Host "Processo $pid encerrado." -ForegroundColor Gray
        }
    }
    Remove-Item $pidsFile -Force
}

Write-Host "Parando infra Docker..." -ForegroundColor Cyan
Set-Location "$ROOT\infra"
docker compose stop postgres redis minio

Write-Host "Tudo encerrado." -ForegroundColor Green
