#!/usr/bin/env bash
# 开发模式:后端 9081(后台)+ Vite HMR 前端 5173(自动代理 /api 到 9081)。
# 用法: scripts/start-web-dev.sh  然后浏览器打开 http://localhost:5173
# 退出脚本时自动清理后台的后端进程。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/2] 启动 pgvector + 后端 9081(后台)..."
docker compose up -d

PY="$ROOT/backend/.venv/bin/python"
[ -x "$PY" ] || PY="$ROOT/backend/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="python"

(
  cd "$ROOT/backend"
  exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 9081
) &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT
sleep 1

echo "[2/2] 启动 Vite 前端(打开 http://localhost:5173)..."
cd "$ROOT/frontend"
npm run dev
