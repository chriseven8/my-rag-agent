import asyncio

from ..config import get_settings
from ..models import ChatRequest, ChatResponse, EvidenceResult, Reference
from ..retrieval.evidence import EvidenceGate
from ..retrieval.pipeline import retrieve_pipeline

SYSTEM_PROMPT = (
    "你是知识库问答助手。只依据提供的【证据】回答用户问题；"
    "引用证据时在对应句末标注来源编号，如 [1][2]。"
    "如果证据不足以回答，直接说明，不要编造。"
)

NO_EVIDENCE_REPLY = "当前文档中没有检索到足够证据，无法回答这个问题。"


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

    def _retrieve(self, query: str) -> tuple[str | None, list[Reference]]:
        """跑双通道检索+证据门控。命中 → (组装好的 user prompt, 引用列表);无证据 → (None, [])。"""
        evidence_result = retrieve_pipeline(
            query,
            vector_channel=self.vector_channel,
            keyword_channel=self.keyword_channel,
            evidence_gate=self.evidence_gate,
            rrf_k=self.settings.rrf_k,
            vector_top_k=self.settings.vector_top_k,
            keyword_top_k=self.settings.keyword_top_k,
        )
        if evidence_result.no_evidence:
            return None, []
        return self._build_user_prompt(query, evidence_result), self._build_references(evidence_result)

    def chat(self, request: ChatRequest) -> ChatResponse:
        user_prompt, references = self._retrieve(request.query)
        if user_prompt is None:
            return ChatResponse(answer=NO_EVIDENCE_REPLY, references=[], no_evidence=True)

        answer = self._call_llm(user_prompt)
        return ChatResponse(answer=answer, references=references, no_evidence=False)

    async def stream_chat(self, request: ChatRequest):
        """SSE 版问答:按事件产出 dict。delta={type,text};done={type,answer,references,no_evidence}。"""
        user_prompt, references = self._retrieve(request.query)
        if user_prompt is None:
            yield {"type": "done", "answer": NO_EVIDENCE_REPLY, "references": [], "no_evidence": True}
            return

        if self.settings.llm_mock:
            # mock:把占位回答分片吐出,模拟打字机
            text = "（mock 回答）根据证据，相关内容如下：" + user_prompt.split("【证据】")[1][:80]
            step = 12
            for i in range(0, len(text), step):
                await asyncio.sleep(0.03)
                yield {"type": "delta", "text": text[i:i + step]}
            yield {"type": "done", "answer": text, "references": [r.model_dump() for r in references], "no_evidence": False}
            return

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
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

    def _call_llm(self, user_prompt: str) -> str:
        if self.settings.llm_mock:
            evidence_head = user_prompt.split("【证据】")[1][:80]
            return "（mock 回答）根据证据，相关内容如下：" + evidence_head
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        return self.llm.invoke(messages).content

    def _build_references(self, evidence_result: EvidenceResult) -> list[Reference]:
        return [
            Reference(index=i, doc_name=ev.doc_name, section_path=ev.section_path, snippet=ev.text[:200])
            for i, ev in enumerate(evidence_result.evidence, start=1)
        ]
