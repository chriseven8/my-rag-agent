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
