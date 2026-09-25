# my-rag-agent

自研检索核心的文档知识库问答系统。FastAPI + LangChain（只做工程管线）+ **手写的双通道检索 / RRF 融合 / 证据门控**。

**不需要任何 API key 就能完整跑通**：默认 `EMBEDDING_MOCK=true` + `LLM_MOCK=true`，用占位向量和占位回答走通「上传 → 解析 → 切块 → 双通道检索 → 流式问答」全链路，方便直接看效果。填上 key 即切换为真实大模型。

## 前置要求

| 依赖 | 版本 | 必要性 |
|---|---|---|
| Python | **≥ 3.10**（开发环境 3.13） | 必须 |
| Docker Desktop | 任意较新版本 | 必须（跑 pgvector） |
| Node.js | ≥ 18 | **可选** —— `frontend/dist` 已随仓库提交，只有想改前端源码时才需要 |

## 快速开始

**第 0 步**：先确认 **Docker Desktop 已经启动**（等托盘图标变绿），否则后端起不来。

**Windows**：双击仓库根目录的 `start-web.bat`。它会启动数据库、等它就绪、必要时构建前端、拉起服务并自动打开浏览器。

**macOS / Linux / git-bash**：

```bash
scripts/start-web.sh
```

两种方式都会打开 <http://127.0.0.1:9081>。关掉窗口即停止服务。

<details>
<summary>手动启动（等价于上面脚本做的事）</summary>

```bash
docker compose up -d --wait            # 起 pgvector 并等 healthcheck 通过
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux 用 .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 9081
```

打开 <http://127.0.0.1:9081> 即可。前端产物 `frontend/dist` 已在仓库里，后端会直接托管它。
</details>

### 想要真实的大模型回答

默认是 mock 模式。要用真实模型，在仓库根目录建 `.env`（可从 `.env.example` 复制）：

```bash
cp .env.example .env
```

填入 `OPENAI_API_KEY`，并把 `EMBEDDING_MOCK` / `LLM_MOCK` 置为 `false`。任何 OpenAI 兼容的服务都行，默认指向 DashScope（`OPENAI_BASE_URL` 改一下就能换 OpenAI/其他）。

> ⚠️ **mock ↔ 真实 embedding 切换后，必须删掉 PG 里旧的向量集合再重建**，否则维度不匹配：
> ```bash
> docker compose exec pgvector psql -U rag -d rag_db -c 'TRUNCATE langchain_pg_embedding, langchain_pg_collection;'
> ```

## 架构

- **PGVector（Docker，端口 5433）** 存 chunk 向量
- **SQLite** 存文档元数据 + 自研倒排索引（BM25，jieba 分词）
- **LangChain** 只用于文档加载/切分/向量库客户端/LLM 客户端
- **`backend/app/retrieval/` 零 LangChain，全部手写**：`vector_channel` / `keyword_channel` / `fusion`（RRF，K=60）/ `evidence`（字符预算裁剪 + 无证据短路，防上下文爆炸与幻觉）

请求链路：

```
上传 → loader(按后缀解析) → splitter(标题感知切块) → PGVector + SQLite 倒排
提问 → (多轮:LLM 指代改写) → 双通道并发检索 → RRF 融合 → 证据门控 → LLM 流式回答(SSE)
```

支持的文档格式：Markdown/纯文本（`.md/.txt`）、PDF（`.pdf`）、Word（`.docx/.docm`）、Excel（`.xlsx/.xlsm`）。只提取文字：Word 保留标题层级与表格、Excel 按 sheet 转行文本；**不做 OCR**，PDF 也不做版面还原，扫描件提取不到内容。

## 测试

```bash
cd backend && python -m pytest -q
```

55 个测试，全部离线且确定（用内存假向量库 + `:memory:` SQLite，不打真实 API）。

## 命令行验证

不用起 Web 服务，直接在终端跑一遍全链路（入库 → 检索 → 问答）：

```bash
python scripts/demo.py README.md      # 支持 .md/.txt/.pdf/.docx/.xlsx
```

## 前端开发模式

改前端源码时用（Vite HMR，自动把 `/api` 代理到 9081）：

```bash
scripts/start-web-dev.sh              # 打开 http://localhost:5173
```

前端源码在 `frontend/src/`：`views/` 两个页面（对话 `/`、文档管理 `/documents`），`api/client.ts` 封装 REST 与 SSE 流式问答，`stores/chat.ts` 把会话状态提到模块作用域（切路由不丢对话）。

> `frontend/dist` 是**故意提交进仓库**的，这样不装 Node 也能直接看页面。改完前端记得 `npm run build` 再提交，否则提交的是旧页面。

## 排错

| 现象 | 原因与处理 |
|---|---|
| `无法连接向量库(pgvector)` / `Connection refused ... 5433` | Docker 没启动。启动 Docker Desktop，然后重新执行启动脚本 |
| 页面显示 `{"detail":"前端未构建..."}` | `frontend/dist` 不存在。执行 `cd frontend && npm run build`（或直接用启动脚本，它会自动构建） |
| 上传后状态一直是「解析中」 | 文件太大或解析失败，看后端窗口日志 |
| `docker compose` 报端口 5433 被占用 | 本机已有别的 Postgres 占了这个端口，改 `docker-compose.yml` 的映射或停掉那个服务 |
