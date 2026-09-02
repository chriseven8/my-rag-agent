from app.models import ScoredChunk
from app.retrieval.evidence import EvidenceGate


def _c(cid, text):
    return ScoredChunk(chunk_id=cid, doc_id="d1", doc_name="doc", section_path="", text=text)


def test_empty_ranked_is_no_evidence():
    gate = EvidenceGate()
    res = gate.build_evidence([])
    assert res.no_evidence is True
    assert res.evidence == []


def test_snippet_truncated():
    gate = EvidenceGate(max_snippet_chars=10)
    res = gate.build_evidence([_c("a", "x" * 100)])
    assert len(res.evidence[0].text) == 10


def test_total_budget_stops():
    gate = EvidenceGate(max_total_chars=40, max_snippet_chars=20)
    res = gate.build_evidence([_c("a", "y" * 20), _c("b", "y" * 20), _c("c", "y" * 20)])
    assert len(res.evidence) == 2


def test_non_empty_not_no_evidence():
    gate = EvidenceGate()
    res = gate.build_evidence([_c("a", "有内容")])
    assert res.no_evidence is False
