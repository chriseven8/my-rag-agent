import asyncio

from ..config import get_settings
from ..models import ChatRequest, ChatResponse, ChatTurn, EvidenceResult, Reference
from ..retrieval.evidence import EvidenceGate
from ..retrieval.pipeline import retrieve_pipeline

SYSTEM_PROMPT = (
    "你是知识库问答助手,直接在对话里回答用户的问题。"
    "只依据提供的【证据】作答,但要用日常说话的方式自然表达:"
    "像同事跟你解释问题那样,可以用完整的句子、必要的过渡和例子,"
    "不要罗列原始条文,不要复述文档原文,不要输出来源、章节、编号等元信息。"
    "结合上面的对话上下文理解用户指的是什么(比如\"它\"\"这个病\"指代什么),"
    "回答要接着上文说,不要每次都从头复述一遍背景。"
    "如果证据不足以回答,直接说明,不要编造。"
)

NO_EVIDENCE_REPLY = "当前文档中没有检索到足够证据，无法回答这个问题。"

# 最多带上多少轮历史(消息条数),避免上下文无限膨胀
MAX_HISTORY_TURNS = 10

# 多轮检索的关键:追问(如"那它有什么症状")单独拿去检索是检索不到东西的,
# 先用一次 LLM 调用把它改写成能独立检索的问题,再进双通道检索。
CONDENSE_PROMPT = (
    "你是检索查询改写器。根据对话历史和用户的最新追问,"
    "把追问改写成一句可以直接用于检索的独立问题:"
    "把\"它\"\"这个病\"这类指代补全成历史里说过的具体对象,必要时带上历史中的主题词。"
    "只输出改写后的问题本身,不要任何解释、引号或前后缀。"
)


class ChatService:
    def __init__(self, vector_channel, keyword_channel, llm, settings=None, evidence_gate: EvidenceGate | None = None):
        self.vector_channel = vector_channel
        self.keyword_channel = keyword_channel
        self.llm = llm
        self.settings = settings or get_settings()
        self.evidence_gate = evidence_gate or EvidenceGate(
            max_total_chars=self.settings.evidence_max_total_chars,
            max_snippet_chars=self.settings.evidence_max_snippet_chars,
        )

    def _contextualize(self, query: str, history: list[ChatTurn]) -> str:
        """把带指代的追问改写成可独立检索的问题;无历史或 mock 模式原样返回。"""
        if not history or self.settings.llm_mock:
            return query
        transcript = "\n".join(f"{t.role}: {t.content}" for t in history[-MAX_HISTORY_TURNS:])
        messages = [
            {"role": "system", "content": CONDENSE_PROMPT},
            {"role": "user", "content": f"对话历史:\n{transcript}\n\n用户追问:{query}"},
        ]
        rewritten = (self.llm.invoke(messages).content or "").strip()
        return rewritten or query

    def _retrieve(self, query: str, history: list[ChatTurn]) -> tuple[str | None, list[Reference], EvidenceResult | None]:
        """跑双通道检索+证据门控。命中 → (user prompt, 引用列表, 证据结果);无证据 → (None, [], None)。"""
        evidence_result = retrieve_pipeline(
            self._contextualize(query, history),
            vector_channel=self.vector_channel,
            keyword_channel=self.keyword_channel,
            evidence_gate=self.evidence_gate,
            rrf_k=self.settings.rrf_k,
            vector_top_k=self.settings.vector_top_k,
            keyword_top_k=self.settings.keyword_top_k,
        )
        if evidence_result.no_evidence:
            return None, [], None
        return (
            self._build_user_prompt(query, evidence_result),
            self._build_references(evidence_result),
            evidence_result,
        )

    def chat(self, request: ChatRequest) -> ChatResponse:
        user_prompt, references, evidence_result = self._retrieve(request.query, request.history)
        if user_prompt is None:
            return ChatResponse(answer=NO_EVIDENCE_REPLY, references=[], no_evidence=True)

        answer = self._call_llm(user_prompt, evidence_result, request.history)
        return ChatResponse(answer=answer, references=references, no_evidence=False)

    async def stream_chat(self, request: ChatRequest):
        """SSE 版问答:按事件产出 dict。delta={type,text};done={type,answer,references,no_evidence}。"""
        # 检索(改写 + embedding HTTP + SQLite)是同步阻塞的,直接在协程里跑会把事件循环
        # 占住整段时间,推流期间其他请求只能排队。丢到线程里跑,循环留着推 SSE。
        user_prompt, references, evidence_result = await asyncio.to_thread(
            self._retrieve, request.query, request.history
        )
        if user_prompt is None:
            yield {"type": "done", "answer": NO_EVIDENCE_REPLY, "references": [], "no_evidence": True}
            return

        if self.settings.llm_mock:
            # mock:把占位回答分片吐出,模拟打字机
            text = self._mock_answer(evidence_result)
            step = 12
            for i in range(0, len(text), step):
                await asyncio.sleep(0.03)
                yield {"type": "delta", "text": text[i:i + step]}
            yield {"type": "done", "answer": text, "references": [r.model_dump() for r in references], "no_evidence": False}
            return

        messages = self._build_messages(user_prompt, request.history)
        answer: list[str] = []
        async for chunk in self.llm.astream(messages):
            piece = getattr(chunk, "content", None) or ""
            if piece:
                answer.append(piece)
                yield {"type": "delta", "text": piece}
        yield {"type": "done", "answer": "".join(answer), "references": [r.model_dump() for r in references], "no_evidence": False}

    def _build_user_prompt(self, query: str, evidence_result: EvidenceResult) -> str:
        blocks = [
            f"[{i}] 来源:{ev.doc_name} 章节:{ev.section_path}\n{ev.text}"
            for i, ev in enumerate(evidence_result.evidence, start=1)
        ]
        return f"问题:{query}\n\n【证据】\n" + "\n\n".join(blocks)

    def _build_messages(self, user_prompt: str, history: list[ChatTurn]) -> list[dict]:
        """system 提示 + 最近若干轮历史 + 本次提问(含证据)。"""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += [{"role": t.role, "content": t.content} for t in history[-MAX_HISTORY_TURNS:]]
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _call_llm(self, user_prompt: str, evidence_result: EvidenceResult, history: list[ChatTurn]) -> str:
        if self.settings.llm_mock:
            return self._mock_answer(evidence_result)
        return self.llm.invoke(self._build_messages(user_prompt, history)).content

    @staticmethod
    def _mock_answer(evidence_result: EvidenceResult) -> str:
        """mock 占位回答:只给首条证据的正文,不拼"（mock 回答）"前缀与"[n] 来源:"抬头。"""
        return evidence_result.evidence[0].text

    def _build_references(self, evidence_result: EvidenceResult) -> list[Reference]:
        return [
            Reference(index=i, doc_name=ev.doc_name, section_path=ev.section_path, snippet=ev.text[:200])
            for i, ev in enumerate(evidence_result.evidence, start=1)
        ]
