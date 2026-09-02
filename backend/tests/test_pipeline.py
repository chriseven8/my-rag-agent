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
