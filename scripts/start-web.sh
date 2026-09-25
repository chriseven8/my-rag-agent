#!/usr/bin/env bash
# 一键启动 RAG Web 页面(单服务:后端 9081 直接托管打包好的前端)。
# 用法: scripts/start-web.sh  然后浏览器打开 http://127.0.0.1:9081
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/3] 启动 pgvector 容器并等待就绪..."
# --wait 会阻塞到容器的 healthcheck 通过为止;失败时直接给出可执行的提示,
# 而不是让后端在 PG 还没起来时报 "Connection refused 5433"。
if ! docker compose up -d --wait --wait-timeout 60; then
  echo
  echo "[错误] pgvector 未能就绪。常见原因:"
  echo "  1. Docker Desktop 没有启动(先启动它,等托盘图标变绿)"
  echo "  2. 5433 端口已被本机另一个 Postgres 占用"
  echo "  启动 Docker 后重新执行本脚本即可。"
  exit 1
fi

echo "[2/3] 检查前端构建产物..."
if [ -f frontend/dist/index.html ]; then
  echo "  frontend/dist 已存在,跳过构建(改过前端源码才需要重新 npm run build)"
else
  echo "  未找到 frontend/dist,开始构建(需要 Node.js)..."
  if [ ! -d frontend/node_modules ]; then
    (cd frontend && npm install)
  fi
  (cd frontend && npm run build)
fi

echo "[3/3] 启动后端并托管页面(打开 http://127.0.0.1:9081)..."
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

cd "$ROOT/backend"
# 用 127.0.0.1 而不是 0.0.0.0:只监听本机,避免 Windows/macOS 弹防火墙授权框
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 9081
