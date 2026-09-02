from ..models import EvidenceResult, ScoredChunk


class EvidenceGate:
    """证据门控:预算裁剪(防上下文爆炸)+ 无证据短路(防幻觉)。"""

    def __init__(self, max_total_chars: int = 4000, max_snippet_chars: int = 500):
        self.max_total_chars = max_total_chars
        self.max_snippet_chars = max_snippet_chars

    def build_evidence(self, ranked: list[ScoredChunk]) -> EvidenceResult:
        if not ranked:
            return EvidenceResult(evidence=[], no_evidence=True)
        total = 0
        kept: list[ScoredChunk] = []
        for item in ranked:
            snippet = item.text[: self.max_snippet_chars]
            if total + len(snippet) > self.max_total_chars:
                break
            kept.append(ScoredChunk(**{**item.model_dump(), "text": snippet}))
            total += len(snippet)
        return EvidenceResult(evidence=kept, no_evidence=False)
