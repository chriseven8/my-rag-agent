# my-rag-agent

自研检索核心的文档知识库问答系统。FastAPI + LangChain(工程管线)+ 自研核心检索(双通道 + RRF + 证据控制)。

## 架构

- **PGVector(Docker)** 存 chunk 向量
- **SQLite** 存文档元数据 + 自研倒排索引(BM25)
- **LangChain** 只做文档加载/切分/向量库/LLM 客户端
- **retrieval/ 零 LangChain,纯手写**:vector_channel / keyword_channel / fusion(RRF, K=60) / evidence(预算+无证据短路)
- **mock 模式默认开启**:`EMBEDDING_MOCK=true` + `LLM_MOCK=true` 时无 API key 也能全链路跑通;切真实模型前先删 PG 里旧的向量集合(`langchain_pg_embedding` 表)重建,避免维度不匹配

## 快速启动

```bash
cp .env.example .env      # 填入真实 OPENAI_API_KEY
docker compose up -d      # 起 pgvector
cd backend && pip install -r requirements.txt
uvicorn app.main:app --port 9081
```

## 验证

```bash
python scripts/demo.py <你的文档.md>   # 例如: python scripts/demo.py README.md
```

## 测试

```bash
cd backend && python -m pytest -v
```

## Web 页面(M4)

浏览器里的「文档管理 + 对话问答」界面。前端 Vue3 + Vite + TypeScript + Element Plus;构建产物由后端直接托管,也支持 dev 模式热更新。mock 模式(默认)无需 API key 即可体验全流程。

**方式一 · 单服务(推荐演示)** — 一个进程托管页面与 API:

```bash
scripts/start-web.sh          # 起 pgvector → 构建前端 → 打开 http://127.0.0.1:9081
```

Windows 不想开终端的话,直接**双击仓库根的 `start-web.bat`** 即可,它会自动开浏览器;关掉弹出的窗口就停止服务。

**方式二 · 开发模式** — 前端 HMR,改代码即时生效:

```bash
scripts/start-web-dev.sh      # 打开 http://localhost:5173(Vite 自动把 /api 代理到 9081)
```

体验路径:文档管理页上传 `.md` → 状态变「已就绪」→ 对话页提问 → 打字机流式回答 + `[1][2]` 引用展示;检索不到证据时返回占位说明。mock 模式回答为占位文本,仅验证链路。

接入真实模型:在仓库根 `.env` 填 `OPENAI_API_KEY`,并把 `EMBEDDING_MOCK`/`LLM_MOCK` 置为 `false`(`.env.example` 可参考)。注意 mock ↔ 真实 embedding 切换后,需删除 PG 里旧的向量集合(`langchain_pg_embedding` 表)重建,否则维度不匹配。

前端源码在 `frontend/src/`:`views/` 两个页面(对话 `/`、文档管理 `/documents`),`api/client.ts` 封装 REST 与 SSE 流式问答。打包产物 `frontend/dist/` 不进版本库。
