"""LLM 工厂:统一在这里决定模型参数,避免散落在 main / service 里各配一套。"""


def build_llm(settings) -> object:
    """按 settings 构造 OpenAI 兼容协议下的对话模型(DashScope 走同一套协议)。"""
    from langchain_openai import ChatOpenAI

    # 只有显式配了 enable_thinking 才带这个参数:非 qwen3 模型不认它,
    # 无脑带上可能直接 400。
    extra_body = (
        {"enable_thinking": settings.enable_thinking}
        if settings.enable_thinking is not None
        else None
    )
    return ChatOpenAI(
        model=settings.chat_model,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        temperature=settings.llm_temperature,
        extra_body=extra_body,
    )
