#!/usr/bin/env bash
# 开发模式:后端 9081(后台)+ Vite HMR 前端 5173(自动代理 /api 到 9081)。
# 用法: scripts/start-web-dev.sh  然后浏览器打开 http://localhost:5173
# 退出脚本时自动清理后台的后端进程。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/2] 启动 pgvector 并等待就绪,然后后台拉起后端 9081..."
if ! docker compose up -d --wait --wait-timeout 60; then
  echo
  echo "[错误] pgvector 未能就绪。先启动 Docker Desktop 再重跑本脚本。"
  exit 1
fi

PY="$ROOT/backend/.venv/bin/python"
[ -x "$PY" ] || PY="$ROOT/backend/.venv/Scripts/python.exe"
if [ ! -x "$PY" ]; then
  echo
  echo "[错误] 没找到后端虚拟环境。请先执行一次:"
  echo "  cd \"$ROOT/backend\""
  echo "  python -m venv .venv"
  echo "  ./.venv/Scripts/python -m pip install -r requirements.txt"
  exit 1
fi

(
  cd "$ROOT/backend"
  exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 9081
) &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT
sleep 2   # 给 uvicorn 一点时间绑定端口,否则 Vite 首个代理请求会 502

echo "[2/2] 启动 Vite 前端(打开 http://localhost:5173)..."
cd "$ROOT/frontend"
npm run dev
