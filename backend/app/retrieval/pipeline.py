from concurrent.futures import ThreadPoolExecutor

from ..models import EvidenceResult
from .evidence import EvidenceGate
from .fusion import rrf_fuse


def retrieve_pipeline(
    query: str,
    *,
    vector_channel,
    keyword_channel,
    evidence_gate: EvidenceGate,
    rrf_k: int = 60,
    vector_top_k: int = 8,
    keyword_top_k: int = 8,
) -> EvidenceResult:
    """双通道并发 → RRF 融合 → 证据门控。

    两路互不依赖:向量那路要发一次 embedding HTTP 请求,关键词那路查 SQLite,
    串行跑就是白等一路。并发后总耗时约等于较慢的那一路。

    两个 channel 的 retrieve 都是同步阻塞的,这里用线程池释放并发
    (vector 是网络等待,自然让出 GIL;keyword 的连接本身带锁、跨线程安全)。
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        vec_future = pool.submit(vector_channel.retrieve, query, top_k=vector_top_k)
        kw_future = pool.submit(keyword_channel.retrieve, query, top_k=keyword_top_k)
        vec, kw = vec_future.result(), kw_future.result()
    fused = rrf_fuse([vec, kw], k=rrf_k)
    return evidence_gate.build_evidence(fused)
