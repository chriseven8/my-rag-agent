import datetime
from pathlib import Path

from ..ingestion.indexer import index_document
from ..ingestion.keyword_index import KeywordIndex
from ..ingestion.loader import load_text
from ..models import DocumentRecord, DocumentStatus


class DocumentService:
    def __init__(
        self,
        upload_dir: str,
        vector_store,
        keyword_index: KeywordIndex,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = vector_store
        self.keyword_index = keyword_index
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _file_path(self, doc_id: str, doc_name: str) -> Path:
        return self.upload_dir / f"{doc_id}{Path(doc_name).suffix}"

    def create(self, filename: str, content: bytes) -> DocumentRecord:
        rec = DocumentRecord(
            doc_id=DocumentRecord.new_id(),
            doc_name=filename,
            status=DocumentStatus.PROCESSING,
            created_at=datetime.datetime.now().isoformat(timespec="seconds"),
        )
        self.keyword_index.upsert_document(rec)
        self._file_path(rec.doc_id, filename).write_bytes(content)
        return rec

    def process(self, doc_id: str) -> None:
        rec = self.keyword_index.get_document(doc_id)
        if not rec:
            return
        try:
            path = self._file_path(rec.doc_id, rec.doc_name)
            text = load_text(str(path))
            index_document(
                doc_id=rec.doc_id,
                doc_name=rec.doc_name,
                text=text,
                vector_store=self.vector_store,
                keyword_index=self.keyword_index,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            self.keyword_index.upsert_document(
                DocumentRecord(**{**rec.model_dump(), "status": DocumentStatus.READY, "error": None})
            )
        except Exception as exc:  # 入库失败 → 标记 failed,不阻塞接口
            self.keyword_index.upsert_document(
                DocumentRecord(**{**rec.model_dump(), "status": DocumentStatus.FAILED, "error": str(exc)})
            )

    def list_all(self) -> list[DocumentRecord]:
        return self.keyword_index.list_documents()

    def get(self, doc_id: str) -> DocumentRecord | None:
        return self.keyword_index.get_document(doc_id)

    def delete(self, doc_id: str) -> None:
        rec = self.keyword_index.get_document(doc_id)
        if not rec:
            return
        chunk_ids = self.keyword_index.delete_document(doc_id)
        if chunk_ids:
            self.vector_store.delete(ids=chunk_ids)
        path = self._file_path(doc_id, rec.doc_name)
        if path.exists():
            path.unlink()
