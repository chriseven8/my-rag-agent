from ..models import ScoredChunk


class VectorChannel:
    """向量检索通道。依赖 duck-typed store(PGVector 满足)提供
    similarity_search_with_score → [(Document, cosine_distance)]。

    similarity = 1 - distance。低于阈值(min_similarity)的直接丢弃。
    """

    def __init__(self, store, min_similarity: float = 0.45):
        self.store = store
        self.min_similarity = min_similarity

    def retrieve(self, query: str, top_k: int = 8) -> list[ScoredChunk]:
        hits = self.store.similarity_search_with_score(query, k=top_k)
        results: list[ScoredChunk] = []
        for doc, distance in hits:
            similarity = 1.0 - distance
            if similarity < self.min_similarity:
                continue
            meta = doc.metadata or {}
            results.append(ScoredChunk(
                chunk_id=meta.get("chunk_id", ""),
                doc_id=meta.get("doc_id", ""),
                doc_name=meta.get("doc_name", ""),
                section_path=meta.get("section_path", ""),
                text=doc.page_content,
                score=similarity,
                channel="vector",
            ))
        return results
