import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..models import Chunk

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
CHAPTER_RE = re.compile(r"^\s*(第[一二三四五六七八九十百\d]+[章节])\s*(.*)$")
SIMPLE_HEADING_RE = re.compile(r"^\s*([一二三四五六七八九十]+)[、.．]\s*(.+)$")


def split_sections(text: str) -> list[tuple[str, str]]:
    """把文本按标题切成 (section_path, section_text) 列表。"""
    sections: list[tuple[str, str]] = []
    stack: list[str] = []
    current_lines: list[str] = []
    current_title = "文档"

    def flush():
        nonlocal current_lines
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_title, body))
        current_lines = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        m = HEADING_RE.match(stripped)
        if m:
            flush()
            level = len(m.group(1))
            while len(stack) >= level:
                stack.pop()
            stack.append(m.group(2).strip())
            current_title = " > ".join(stack)
            continue
        cm = CHAPTER_RE.match(stripped) or SIMPLE_HEADING_RE.match(stripped)
        if cm and len(stripped) < 30:
            flush()
            current_title = stripped
            continue
        current_lines.append(raw_line)
    flush()
    return sections


def split_text(text: str, *, doc_id: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[Chunk]:
    """标题感知切块:先按标题分节,节内用 RecursiveCharacterTextSplitter 再切。"""
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks: list[Chunk] = []
    index = 0
    for section_path, section_text in split_sections(text):
        pieces = splitter.split_text(section_text) if section_text else []
        if not pieces:
            pieces = [section_text]
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(Chunk(
                doc_id=doc_id,
                chunk_id=f"{doc_id}-{index}",
                section_path=section_path,
                chunk_index=index,
                text=piece,
            ))
            index += 1
    return chunks
