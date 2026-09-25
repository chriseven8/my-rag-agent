import os

import pytest

# 测试必须离线且确定:.env 里切成真实模型后,Settings 仍会读它,
# 因此这里在用 Settings 之前强制回 mock,避免测试去打真实 API。
os.environ["EMBEDDING_MOCK"] = "true"
os.environ["LLM_MOCK"] = "true"

# ChatOpenAI 在**构造时**就校验 api_key 非空(哪怕一个请求都不发),
# 而 test_llm.py 只断言构造参数、不联网。纯净 clone 没有 .env,
# openai_api_key 默认为 "",构造即抛 OpenAIError → 测试红。塞个假 key 兜住。
# 这里用 setdefault:本地 .env 有真 key 时不去覆盖它。
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")


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
