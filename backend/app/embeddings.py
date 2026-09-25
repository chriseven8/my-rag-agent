"""embedding 工厂:默认 mock(无 key 也能入库/检索),配好 key 后切真实。"""


class FakeEmbedder:
    """占位 embedding:返回固定向量。无 key 时检索语义靠关键词通道,向量通道只演示流程。"""

    def __init__(self, dim: int = 8):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.01] * self.dim for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.01] * self.dim


def build_embedder(settings) -> object:
    """按 settings 返回 mock 或真实 embedding(OpenAI 兼容协议)。"""
    if settings.embedding_mock:
        return FakeEmbedder(settings.embedding_dim)
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        # 关掉本地 tiktoken 长度校验:DashScope 服务端自己分词,
        # 且 tiktoken 需从 openaipublic 下载字典,网络不通时会直接报 SSLError。
        check_embedding_ctx_length=False,
    )
