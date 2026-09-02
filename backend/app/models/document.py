import uuid
from enum import Enum

from pydantic import BaseModel


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentRecord(BaseModel):
    doc_id: str
    doc_name: str
    status: DocumentStatus
    created_at: str
    error: str | None = None

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex


class Chunk(BaseModel):
    doc_id: str
    chunk_id: str
    section_path: str = ""
    chunk_index: int = 0
    text: str
