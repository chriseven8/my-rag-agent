from app.ingestion.keyword_index import KeywordIndex
from app.models import Chunk


def _chunks(texts):
    return [
        Chunk(doc_id="d1", chunk_id=f"d1-{i}", chunk_index=i, section_path="", text=t)
        for i, t in enumerate(texts)
    ]


def test_bm25_ranks_combined_term_first():
    idx = KeywordIndex(":memory:")
    idx.add_chunks("d1", _chunks(["苹果 价格 很贵", "香蕉 价格 便宜", "苹果 电脑 性能 好"]))
    res = idx.bm25_search("苹果 价格")
    assert res, "应有结果"
    assert res[0].chunk_id == "d1-0"  # 同时命中 苹果+价格


def test_no_match_returns_empty():
    idx = KeywordIndex(":memory:")
    idx.add_chunks("d1", _chunks(["苹果 价格 很贵"]))
    assert idx.bm25_search("完全不存在 的词") == []


def test_rare_term_idf_boost():
    idx = KeywordIndex(":memory:")
    idx.add_chunks("d1", _chunks(["苹果 价格 很贵", "香蕉 价格 便宜", "苹果 电脑 性能 好"]))
    res = idx.bm25_search("性能")
    assert res and res[0].chunk_id == "d1-2"


def test_longer_doc_penalized():
    # 相同词频(tf=1)下,长文档因长度归一化(b=0.75)排更后
    idx = KeywordIndex(":memory:")
    idx.add_chunks("d1", [
        Chunk(doc_id="d1", chunk_id="d1-0", chunk_index=0, text="性能 好"),
        Chunk(doc_id="d1", chunk_id="d1-1", chunk_index=1, text="性能 " + "无关 填充 " * 6),
    ])
    res = idx.bm25_search("性能")
    assert res and res[0].chunk_id == "d1-0"


def test_document_lifecycle():
    idx = KeywordIndex(":memory:")
    idx.add_chunks("d1", _chunks(["苹果 价格"]))
    from app.models import DocumentRecord, DocumentStatus
    idx.upsert_document(DocumentRecord(doc_id="d1", doc_name="a.txt", status=DocumentStatus.READY, created_at="now"))
    assert len(idx.list_documents()) == 1
    chunk_ids = idx.delete_document("d1")
    assert chunk_ids == ["d1-0"]
    assert idx.bm25_search("苹果") == []
