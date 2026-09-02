from ..models import EvidenceResult
from .evidence import EvidenceGate
from .fusion import rrf_fuse


def retrieve_pipeline(
    query: str,
    *,
    vector_channel,
    keyword_channel,
    evidence_gate: EvidenceGate,
    rrf_k: int = 60,
    vector_top_k: int = 8,
    keyword_top_k: int = 8,
) -> EvidenceResult:
    """双通道并行 → RRF 融合 → 证据门控。"""
    vec = vector_channel.retrieve(query, top_k=vector_top_k)
    kw = keyword_channel.retrieve(query, top_k=keyword_top_k)
    fused = rrf_fuse([vec, kw], k=rrf_k)
    return evidence_gate.build_evidence(fused)
