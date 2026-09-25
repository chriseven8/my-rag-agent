"""命令行演示:入库一份文档 → 双通道检索 → 证据驱动问答。用法:
    python scripts/demo.py <文档路径> [--db 可选sqlite路径]
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from langchain_community.vectorstores import PGVector  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.embeddings import build_embedder  # noqa: E402
from app.ingestion.indexer import index_document  # noqa: E402
from app.ingestion.keyword_index import KeywordIndex  # noqa: E402
from app.ingestion.loader import load_text  # noqa: E402
from app.llm import build_llm  # noqa: E402
from app.models import ChatRequest, DocumentRecord, DocumentStatus  # noqa: E402
from app.retrieval.evidence import EvidenceGate  # noqa: E402
from app.retrieval.keyword_channel import KeywordChannel  # noqa: E402
from app.retrieval.pipeline import retrieve_pipeline  # noqa: E402
from app.retrieval.vector_channel import VectorChannel  # noqa: E402
from app.service.chat_service import ChatService  # noqa: E402


def main(file_path: str, db: str) -> None:
    settings = get_settings()
    print("[1/4] 初始化 SQLite 倒排索引 + PGVector ...")
    keyword_index = KeywordIndex(db or settings.sqlite_path)
    embedder = build_embedder(settings)
    vector_store = PGVector(
        connection_string=settings.pg_connection_string,
        embedding_function=embedder,
        collection_name="my_rag_chunks",
        distance_strategy="cosine",
    )

    print(f"[2/4] 入库 {file_path} ...")
    text = load_text(file_path)
    doc_id = DocumentRecord.new_id()
    keyword_index.upsert_document(DocumentRecord(
        doc_id=doc_id,
        doc_name=os.path.basename(file_path),
        status=DocumentStatus.READY,
        created_at=datetime.datetime.now().isoformat(timespec="seconds"),
    ))
    chunks = index_document(
        doc_id=doc_id,
        doc_name=os.path.basename(file_path),
        text=text,
        vector_store=vector_store,
        keyword_index=keyword_index,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    print(f"      生成 {len(chunks)} 个 chunk")

    vec_ch = VectorChannel(vector_store, min_similarity=settings.vector_min_similarity)
    kw_ch = KeywordChannel(keyword_index, relative_floor=settings.keyword_relative_score_floor)
    chat_service = ChatService(
        vector_channel=vec_ch,
        keyword_channel=kw_ch,
        llm=build_llm(settings),
    )

    print("[3/4] 检索演示(双通道 + RRF):")
    for q in ["价格", "规则"]:
        ev = retrieve_pipeline(
            q,
            vector_channel=vec_ch,
            keyword_channel=kw_ch,
            evidence_gate=EvidenceGate(
                max_total_chars=settings.evidence_max_total_chars,
                max_snippet_chars=settings.evidence_max_snippet_chars,
            ),
            rrf_k=settings.rrf_k,
            vector_top_k=settings.vector_top_k,
            keyword_top_k=settings.keyword_top_k,
        )
        print(f"      问题「{q}」→ 召回 {len(ev.evidence)} 条证据, no_evidence={ev.no_evidence}")

    print("[4/4] 问答演示:")
    resp = chat_service.chat(ChatRequest(query="价格"))
    print("      answer:", resp.answer[:200])
    for ref in resp.references:
        print(f"      [{ref.index}] {ref.doc_name} | {ref.section_path} | {ref.snippet[:60]}...")

    if settings.llm_mock:
        print("\n提示: 当前 LLM_MOCK=true,回答为占位。填入真实 OPENAI_API_KEY 并设 LLM_MOCK=false 得到真实回答。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="my-rag-agent 全链路演示")
    parser.add_argument("file", help="要入库的文档路径(md/txt/pdf/docx/xlsx)")
    parser.add_argument("--db", default=None, help="覆盖 SQLite 路径(默认取 .env 的 sqlite_path)")
    args = parser.parse_args()
    main(args.file, args.db)
