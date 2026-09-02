from app.ingestion.keyword_index import KeywordIndex
from app.models import Chunk
from app.retrieval.keyword_channel import KeywordChannel


def _idx():
    idx = KeywordIndex(":memory:")
    idx.add_chunks("d1", [
        Chunk(doc_id="d1", chunk_id="d1-0", chunk_index=0, text="苹果 价格 很贵"),
        Chunk(doc_id="d1", chunk_id="d1-1", chunk_index=1, text="香蕉 价格 便宜"),
        Chunk(doc_id="d1", chunk_id="d1-2", chunk_index=2, text="苹果 电脑 性能 好"),
    ])
    return idx


def test_returns_top_result():
    ch = KeywordChannel(_idx())
    out = ch.retrieve("苹果 价格", top_k=8)
    assert out and out[0].chunk_id == "d1-0"


def test_relative_floor_filters_weak():
    idx = _idx()
    idx.add_chunks("d1", [Chunk(doc_id="d1", chunk_id="d1-3", chunk_index=3, text="普通 内容 无关")])
    ch = KeywordChannel(idx, relative_floor=0.9)
    out = ch.retrieve("苹果 价格", top_k=8)
    assert out
    assert all(c.score >= out[0].score * 0.9 for c in out)
    assert len(out) < 4  # 高阈值把弱匹配过滤了


def test_no_match_empty():
    ch = KeywordChannel(_idx())
    assert ch.retrieve("完全不存在 的词") == []
