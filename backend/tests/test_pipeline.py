import threading

from app.models import ScoredChunk
from app.retrieval.evidence import EvidenceGate
from app.retrieval.pipeline import retrieve_pipeline


class FakeChannel:
    def __init__(self, results):
        self.results = results

    def retrieve(self, query, top_k=8):
        return self.results


def test_pipeline_hybrid_label():
    vec = FakeChannel([ScoredChunk(chunk_id="a", doc_id="d", doc_name="doc", section_path="", text="ta", channel="vector")])
    kw = FakeChannel([ScoredChunk(chunk_id="a", doc_id="d", doc_name="doc", section_path="", text="ta", channel="keyword")])
    res = retrieve_pipeline("q", vector_channel=vec, keyword_channel=kw, evidence_gate=EvidenceGate())
    assert res.no_evidence is False
    assert res.evidence[0].channel == "hybrid"


def test_pipeline_no_evidence():
    vec = FakeChannel([])
    kw = FakeChannel([])
    res = retrieve_pipeline("q", vector_channel=vec, keyword_channel=kw, evidence_gate=EvidenceGate())
    assert res.no_evidence is True


class BarrierChannel:
    """两路检索互不依赖,串行跑就是白等一路。用栅栏卡住:只有真并发才能两边同时到齐。"""

    def __init__(self, barrier):
        self.barrier = barrier
        self.called = False

    def retrieve(self, query, top_k=8):
        self.barrier.wait(timeout=10)  # 串行执行时对端永远不来 → BrokenBarrierError
        self.called = True
        return []


def test_dual_channels_run_concurrently():
    barrier = threading.Barrier(2)
    vec = BarrierChannel(barrier)
    kw = BarrierChannel(barrier)

    retrieve_pipeline("q", vector_channel=vec, keyword_channel=kw, evidence_gate=EvidenceGate())

    assert vec.called and kw.called


class RecordingTopKChannel:
    def __init__(self, results):
        self.results = results
        self.seen_top_k = None

    def retrieve(self, query, top_k=8):
        self.seen_top_k = top_k
        return self.results


def test_pipeline_passes_per_channel_top_k():
    """并发化后容易把 top_k 传丢(或被两路共用),这里钉住各自的路由。"""
    vec = RecordingTopKChannel([])
    kw = RecordingTopKChannel([])

    retrieve_pipeline(
        "q", vector_channel=vec, keyword_channel=kw, evidence_gate=EvidenceGate(),
        vector_top_k=3, keyword_top_k=7,
    )

    assert vec.seen_top_k == 3
    assert kw.seen_top_k == 7
