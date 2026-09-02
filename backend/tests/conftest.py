import pytest


class FakeEmbedder:
    """固定 8 维向量,零依赖,让测试不碰真实 embedding API。"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.01] * 8 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.01] * 8


class FakeVectorStore:
    """内存版 PGVector,实现 add_texts/delete/similarity_search_with_score。"""

    def __init__(self):
        self.docs: dict[str, tuple[str, dict, float]] = {}  # chunk_id -> (text, metadata, score)

    def add_texts(self, texts, metadatas=None, ids=None, **kwargs):
        metadatas = metadatas or [{}] * len(texts)
        ids = ids or [f"id-{i}" for i in range(len(texts))]
        for text, meta, cid in zip(texts, metadatas, ids):
            self.docs[cid] = (text, meta, 0.0)
        return list(ids)

    def delete(self, ids=None, **kwargs):
        for cid in ids or []:
            self.docs.pop(cid, None)

    def similarity_search_with_score(self, query, k=4, **kwargs):
        class _Doc:
            pass
        hits = []
        for cid, (text, meta, _score) in list(self.docs.items())[:k]:
            d = _Doc()
            d.page_content = text
            d.metadata = meta
            hits.append((d, 0.05))  # 余弦距离 0.05 → 相似度 0.95
        return hits


@pytest.fixture
def vector_store():
    return FakeVectorStore()


@pytest.fixture
def embedder():
    return FakeEmbedder()
