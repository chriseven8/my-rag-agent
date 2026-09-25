import asyncio
import threading

from app.config import Settings
from app.ingestion.indexer import index_document
from app.ingestion.keyword_index import KeywordIndex
from app.models import ChatRequest, ChatTurn, EvidenceResult
from app.retrieval.evidence import EvidenceGate
from app.retrieval.keyword_channel import KeywordChannel
from app.retrieval.pipeline import retrieve_pipeline
from app.retrieval.vector_channel import VectorChannel
from app.service import chat_service
from app.service.chat_service import MAX_HISTORY_TURNS, ChatService, NO_EVIDENCE_REPLY


class FakeLLM:
    def invoke(self, messages):
        return type("R", (), {"content": "（测试回答）根据证据说明。来源[1]。"})()


class RecordingLLM:
    """记录收到的 messages,用于断言历史是否被带上。"""

    def __init__(self):
        self.messages = []

    def invoke(self, messages):
        self.messages = messages
        return type("R", (), {"content": "苹果的价格是 3000 元。"})()


def _no_mock_settings():
    """显式关掉 mock:否则 _call_llm 走占位分支,永远碰不到 FakeLLM。"""
    return Settings(llm_mock=False)


def _build_service(store, idx, llm=None, settings=None):
    vec = VectorChannel(store, min_similarity=0.45)
    kw = KeywordChannel(idx, relative_floor=0.35)
    return ChatService(vector_channel=vec, keyword_channel=kw, llm=llm or FakeLLM(),
                       settings=settings, evidence_gate=EvidenceGate(max_total_chars=4000, max_snippet_chars=500))


def _index_one_chunk(store, idx, text="# 第一章\n苹果 价格 是 3000 元"):
    index_document(doc_id="d1", doc_name="手册.md", text=text,
                   vector_store=store, keyword_index=idx)


def test_chat_passes_history_to_llm(vector_store):
    idx = KeywordIndex(":memory:")
    _index_one_chunk(vector_store, idx)
    llm = RecordingLLM()
    svc = _build_service(vector_store, idx, llm=llm, settings=_no_mock_settings())

    svc.chat(ChatRequest(
        query="那它贵吗",
        history=[
            ChatTurn(role="user", content="苹果多少钱"),
            ChatTurn(role="assistant", content="苹果 3000 元。"),
        ],
    ))

    assert [m["role"] for m in llm.messages] == ["system", "user", "assistant", "user"]
    assert llm.messages[1]["content"] == "苹果多少钱"
    assert llm.messages[2]["content"] == "苹果 3000 元。"
    assert "【证据】" in llm.messages[3]["content"]


def test_chat_keeps_only_recent_history(vector_store):
    idx = KeywordIndex(":memory:")
    _index_one_chunk(vector_store, idx)
    llm = RecordingLLM()
    svc = _build_service(vector_store, idx, llm=llm, settings=_no_mock_settings())

    history = [ChatTurn(role="user", content=f"第{i}问") for i in range(MAX_HISTORY_TURNS + 5)]
    svc.chat(ChatRequest(query="那它贵吗", history=history))

    # system + 最近 MAX_HISTORY_TURNS 条 + 当前提问
    assert len(llm.messages) == 1 + MAX_HISTORY_TURNS + 1
    assert llm.messages[1]["content"] == f"第{len(history) - MAX_HISTORY_TURNS}问"


class SpyChannel:
    """记录检索时实际用到的 query。"""

    def __init__(self):
        self.queries = []

    def retrieve(self, query, top_k=8):
        self.queries.append(query)
        return []


class RewritingLLM:
    """首次调用返回改写结果(无证据时会短路,不会再有第二次调用)。"""

    def __init__(self, rewritten):
        self.rewritten = rewritten
        self.messages = []

    def invoke(self, messages):
        self.messages.append(messages)
        return type("R", (), {"content": self.rewritten})()


def _probe_service(llm, settings):
    vec, kw = SpyChannel(), SpyChannel()
    svc = ChatService(
        vector_channel=vec, keyword_channel=kw, llm=llm, settings=settings,
        evidence_gate=EvidenceGate(max_total_chars=4000, max_snippet_chars=500),
    )
    return svc, vec, kw


def test_followup_is_rewritten_before_retrieval():
    """带指代的追问先改写成独立问题再检索,否则历史等于白给。"""
    llm = RewritingLLM("慢性胃炎的常见症状")
    svc, vec, kw = _probe_service(llm, _no_mock_settings())

    svc.chat(ChatRequest(
        query="那它有什么症状",
        history=[ChatTurn(role="user", content="慢性胃炎是什么")],
    ))

    assert vec.queries == ["慢性胃炎的常见症状"]
    assert kw.queries == ["慢性胃炎的常见症状"]


def test_no_history_skips_rewrite():
    llm = RewritingLLM("不该被用到")
    svc, vec, kw = _probe_service(llm, _no_mock_settings())

    svc.chat(ChatRequest(query="苹果 价格"))

    assert vec.queries == ["苹果 价格"]
    assert llm.messages == []  # 没有历史就不该多花一次改写调用


def test_mock_mode_skips_rewrite():
    llm = RewritingLLM("不该被用到")
    svc, vec, kw = _probe_service(llm, Settings(llm_mock=True))

    svc.chat(ChatRequest(
        query="那它有什么症状",
        history=[ChatTurn(role="user", content="慢性胃炎是什么")],
    ))

    assert vec.queries == ["那它有什么症状"]
    assert llm.messages == []


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


def test_stream_retrieval_runs_off_the_event_loop(monkeypatch):
    """检索是同步阻塞的(embedding 要发 HTTP、关键词查 SQLite + jieba 分词)。

    直接在协程里 await 会占死事件循环:SSE 推流期间其他请求全排在后面。
    必须丢到线程里跑 —— 这里断言检索阶段不在事件循环那个线程上执行。
    """
    seen: dict[str, int] = {}

    def fake_pipeline(query, **kwargs):
        seen.setdefault("retrieve", threading.get_ident())
        return EvidenceResult(no_evidence=True)

    monkeypatch.setattr(chat_service, "retrieve_pipeline", fake_pipeline)

    async def main():
        seen["loop"] = threading.get_ident()
        svc = ChatService(
            vector_channel=SpyChannel(), keyword_channel=SpyChannel(),
            llm=FakeLLM(), settings=Settings(llm_mock=True),
        )
        async for _ in svc.stream_chat(ChatRequest(query="q")):
            pass

    asyncio.run(main())

    assert "retrieve" in seen
    assert seen["retrieve"] != seen["loop"]
