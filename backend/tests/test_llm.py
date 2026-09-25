from app.config import Settings
from app.llm import build_llm


def test_thinking_disabled_when_configured_false():
    """qwen3 系列默认开思考,token 在出正文前先吐一大段 reasoning,TTFT 直接多好几秒。

    实测 qwen3.7-plus:thinking=ON TTFT 8.6s / OFF 1.25s,故默认必须关。
    """
    llm = build_llm(Settings(enable_thinking=False))

    assert llm.extra_body == {"enable_thinking": False}


def test_thinking_flag_omitted_when_unset():
    """不配就不带 extra_body:有些(非 qwen3)模型不认这个参数,带上可能直接报错。"""
    llm = build_llm(Settings(enable_thinking=None))

    assert not llm.extra_body


def test_thinking_flag_can_be_turned_back_on():
    """留个开关:需要模型多想一步的场合还能开回来。"""
    llm = build_llm(Settings(enable_thinking=True))

    assert llm.extra_body == {"enable_thinking": True}


def test_llm_uses_configured_model_and_temperature():
    llm = build_llm(Settings(chat_model="qwen3.7-plus", llm_temperature=0.5))

    assert llm.model_name == "qwen3.7-plus"
    assert llm.temperature == 0.5
