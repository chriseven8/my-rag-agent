#!/usr/bin/env bash
# 一键启动 RAG Web 页面(单服务:后端 9081 直接托管打包好的前端)。
# 用法: scripts/start-web.sh  然后浏览器打开 http://127.0.0.1:9081
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/3] 启动 pgvector 容器..."
docker compose up -d

echo "[2/3] 构建前端(首次会自动 npm install)..."
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi
(cd frontend && npm run build)

echo "[3/3] 启动后端并托管页面(打开 http://127.0.0.1:9081)..."
PY="$ROOT/backend/.venv/bin/python"
[ -x "$PY" ] || PY="$ROOT/backend/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="python"

cd "$ROOT/backend"
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 9081
