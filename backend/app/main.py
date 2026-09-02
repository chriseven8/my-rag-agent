from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from langchain_community.vectorstores import PGVector
from langchain_openai import ChatOpenAI

from .api import chat, documents
from .config import get_settings
from .embeddings import build_embedder
from .ingestion.keyword_index import KeywordIndex
from .retrieval.keyword_channel import KeywordChannel
from .retrieval.vector_channel import VectorChannel
from .service.chat_service import ChatService
from .service.document_service import DocumentService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    embedder = build_embedder(settings)
    vector_store = PGVector(
        connection_string=settings.pg_connection_string,
        embedding_function=embedder,
        collection_name="my_rag_chunks",
        distance_strategy="cosine",
    )
    keyword_index = KeywordIndex(settings.sqlite_path)
    document_service = DocumentService(
        upload_dir="data/uploads", vector_store=vector_store, keyword_index=keyword_index
    )
    vector_channel = VectorChannel(vector_store, min_similarity=settings.vector_min_similarity)
    keyword_channel = KeywordChannel(keyword_index, relative_floor=settings.keyword_relative_score_floor)
    llm = ChatOpenAI(
        model=settings.chat_model,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    chat_service = ChatService(
        vector_channel=vector_channel, keyword_channel=keyword_channel, llm=llm
    )

    app.state.document_service = document_service
    app.state.chat_service = chat_service
    yield


app = FastAPI(title="my-rag-agent", lifespan=lifespan)

# CORS:允许前端 dev 模式(Vite 5173)跨域调用
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 前端未命中路由一律回退 index.html(SPA 客户端路由),非前端路径返回标准 404
_NON_SPA_PREFIXES = {"api", "docs", "redoc", "openapi.json"}


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    first = full_path.split("/", 1)[0] if full_path else ""
    if first in _NON_SPA_PREFIXES:
        raise HTTPException(status_code=404, detail="Not Found")
    dist = Path(get_settings().frontend_dist)
    if not dist.is_dir():
        return JSONResponse(
            status_code=503,
            content={"detail": "前端未构建:请先在 frontend/ 下执行 npm run build"},
        )
    target = (dist / full_path).resolve()
    if full_path and target.is_file() and dist in target.parents:
        return FileResponse(target)
    return FileResponse(dist / "index.html")
