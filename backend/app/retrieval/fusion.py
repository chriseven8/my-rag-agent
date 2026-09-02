from ..models import ScoredChunk


def rrf_fuse(ranked_lists: list[list[ScoredChunk]], k: int = 60) -> list[ScoredChunk]:
    """Reciprocal Rank Fusion:score = Σ 1/(k + rank + 1)。

    为什么不加权分数相加?因为各通道分数量纲不同(余弦 vs BM25),RRF 只看排名、天然归一化。
    """
    scores: dict[str, float] = {}
    by_id: dict[str, ScoredChunk] = {}
    channels: dict[str, set[str]] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1.0 / (k + rank + 1)
            by_id.setdefault(item.chunk_id, item)
            channels.setdefault(item.chunk_id, set()).add(item.channel)
    merged: list[ScoredChunk] = []
    for cid in sorted(scores, key=lambda c: -scores[c]):
        item = by_id[cid]
        item.score = scores[cid]
        item.channel = "hybrid" if len(channels[cid]) > 1 else next(iter(channels[cid]))
        merged.append(item)
    return merged
