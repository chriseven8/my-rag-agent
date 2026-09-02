from pydantic import BaseModel


class ScoredChunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_name: str
    section_path: str
    text: str
    score: float = 0.0
    channel: str = ""


class EvidenceResult(BaseModel):
    evidence: list[ScoredChunk] = []
    no_evidence: bool = False


class Reference(BaseModel):
    index: int
    doc_name: str
    section_path: str
    snippet: str


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    references: list[Reference] = []
    no_evidence: bool = False
