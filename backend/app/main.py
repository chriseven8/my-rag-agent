from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_community.vectorstores import PGVector
from langchain_community.vectorstores.utils import DistanceStrategy
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
        distance_strategy=DistanceStrategy.COSINE,
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
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
