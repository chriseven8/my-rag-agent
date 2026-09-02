from ..models import Chunk
from .keyword_index import KeywordIndex
from .splitter import split_text


def index_document(
    *,
    doc_id: str,
    doc_name: str,
    text: str,
    vector_store,
    keyword_index: KeywordIndex,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[Chunk]:
    """切块 → 写入 PGVector(向量) + SQLite(倒排)。返回生成的 chunks。"""
    chunks = split_text(text, doc_id=doc_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        return []
    metadatas = [
        {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "chunk_id": c.chunk_id,
            "chunk_index": c.chunk_index,
            "section_path": c.section_path,
        }
        for c in chunks
    ]
    vector_store.add_texts(texts=[c.text for c in chunks], metadatas=metadatas, ids=[c.chunk_id for c in chunks])
    keyword_index.add_chunks(doc_id, chunks)
    return chunks
