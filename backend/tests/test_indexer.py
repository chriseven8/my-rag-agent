from app.ingestion.indexer import index_document
from app.ingestion.keyword_index import KeywordIndex


def test_index_document_populates_both_stores(vector_store, embedder):
    idx = KeywordIndex(":memory:")
    chunks = index_document(
        doc_id="d1",
        doc_name="手册.md",
        text="# 第一章\n退款规则是三天内\n\n# 第二章\n发货规则是五天",
        vector_store=vector_store,
        keyword_index=idx,
    )
    assert chunks, "应生成 chunk"
    assert len(vector_store.docs) == len(chunks)
    # 每个 chunk 都进了倒排
    for c in chunks:
        assert c.chunk_id in vector_store.docs
    assert idx.bm25_search("退款") != []


def test_index_embeds_with_section_path(vector_store, embedder):
    idx = KeywordIndex(":memory:")
    chunks = index_document(
        doc_id="d1", doc_name="手册.md", text="# 第一章\n退款规则",
        vector_store=vector_store, keyword_index=idx,
    )
    meta = vector_store.docs[chunks[0].chunk_id][1]
    assert meta["section_path"] == "第一章"
    assert meta["doc_name"] == "手册.md"
