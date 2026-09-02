import pytest

from app.retrieval.vector_channel import VectorChannel


class _Doc:
    def __init__(self, metadata, content="text"):
        self.metadata = metadata
        self.page_content = content


def test_filters_below_min_similarity():
    class FakeStore:
        def similarity_search_with_score(self, query, k=8):
            # 距离 0.1 → 相似度 0.9(保留);距离 0.7 → 相似度 0.3(过滤)
            return [
                (_Doc({"chunk_id": "c1", "doc_id": "d1", "doc_name": "doc", "section_path": "s"}), 0.1),
                (_Doc({"chunk_id": "c2", "doc_id": "d1", "doc_name": "doc", "section_path": "s"}), 0.7),
            ]

    channel = VectorChannel(FakeStore(), min_similarity=0.45)
    out = channel.retrieve("q", top_k=8)
    assert len(out) == 1
    assert out[0].chunk_id == "c1"
    assert out[0].score == pytest.approx(0.9)


def test_empty_store_returns_empty():
    class EmptyStore:
        def similarity_search_with_score(self, query, k=8):
            return []

    channel = VectorChannel(EmptyStore(), min_similarity=0.45)
    assert channel.retrieve("q") == []
