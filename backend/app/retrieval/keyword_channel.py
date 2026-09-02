from ..models import ScoredChunk


class KeywordChannel:
    """关键词检索通道:BM25 粗召回 → 相对阈值过滤(低于最高分 floor 的直接丢)。"""

    def __init__(self, index, relative_floor: float = 0.35):
        self.index = index
        self.relative_floor = relative_floor

    def retrieve(self, query: str, top_k: int = 8) -> list[ScoredChunk]:
        candidates = self.index.bm25_search(query, top_k=max(top_k * 2, 16))
        if not candidates:
            return []
        threshold = candidates[0].score * self.relative_floor
        return [c for c in candidates if c.score >= threshold][:top_k]
