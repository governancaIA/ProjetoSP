#!/bin/bash
# FiscalAI — inicia frontend e backend em localhost

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Backend: http://localhost:8000"
cd "$ROOT/backend"
python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "==> Frontend: http://localhost:5173"
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend PID: $BACKEND_PID  |  Frontend PID: $FRONTEND_PID"
echo "Pressione Ctrl+C para parar ambos."

# Ao sair, mata os dois processos
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Serviços encerrados.'" EXIT
wait
