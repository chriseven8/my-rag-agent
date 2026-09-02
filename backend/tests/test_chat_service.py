from app.ingestion.keyword_index import KeywordIndex
from app.models import ChatRequest, Chunk
from app.retrieval.evidence import EvidenceGate
from app.retrieval.keyword_channel import KeywordChannel
from app.retrieval.pipeline import retrieve_pipeline
from app.retrieval.vector_channel import VectorChannel
from app.service.chat_service import ChatService, NO_EVIDENCE_REPLY


class FakeLLM:
    def invoke(self, messages):
        return type("R", (), {"content": "（测试回答）根据证据说明。来源[1]。"})()


def _build_service(store, idx):
    vec = VectorChannel(store, min_similarity=0.45)
    kw = KeywordChannel(idx, relative_floor=0.35)
    return ChatService(vector_channel=vec, keyword_channel=kw, llm=FakeLLM(),
                       settings=None, evidence_gate=EvidenceGate(max_total_chars=4000, max_snippet_chars=500))


def test_chat_returns_answer_and_references(vector_store):
    idx = KeywordIndex(":memory:")
    from app.ingestion.indexer import index_document
    index_document(doc_id="d1", doc_name="手册.md", text="# 第一章\n苹果 价格 是 3000 元",
                   vector_store=vector_store, keyword_index=idx)
    svc = _build_service(vector_store, idx)
    resp = svc.chat(ChatRequest(query="苹果 价格"))
    assert resp.no_evidence is False
    assert resp.answer
    assert resp.references
    assert resp.references[0].index == 1


def test_chat_no_evidence_reply(vector_store):
    idx = KeywordIndex(":memory:")
    svc = _build_service(vector_store, idx)
    resp = svc.chat(ChatRequest(query="完全不存在的词"))
    assert resp.no_evidence is True
    assert resp.answer == NO_EVIDENCE_REPLY
