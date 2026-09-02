from app.models import ScoredChunk
from app.retrieval.fusion import rrf_fuse


def _c(cid, channel):
    return ScoredChunk(chunk_id=cid, doc_id="d1", doc_name="doc", section_path="", text="t", channel=channel)


def test_rank_1_combination_wins():
    vec = [_c("a", "vector"), _c("b", "vector"), _c("c", "vector")]
    kw = [_c("a", "keyword"), _c("c", "keyword")]
    out = rrf_fuse([vec, kw], k=60)
    # a: 1/61+1/61 最高;c: 1/63+1/62 次之(双通道都命中);b: 1/62 只在向量
    assert [x.chunk_id for x in out] == ["a", "c", "b"]


def test_hybrid_channel_label():
    vec = [_c("a", "vector")]
    kw = [_c("a", "keyword")]
    out = rrf_fuse([vec, kw])
    assert out[0].channel == "hybrid"


def test_single_channel_preserves_order():
    vec = [_c("x", "vector"), _c("y", "vector")]
    out = rrf_fuse([vec])
    assert [x.chunk_id for x in out] == ["x", "y"]


def test_score_is_rrf_score():
    vec = [_c("a", "vector")]
    out = rrf_fuse([vec], k=60)
    assert abs(out[0].score - 1 / 61) < 1e-9
