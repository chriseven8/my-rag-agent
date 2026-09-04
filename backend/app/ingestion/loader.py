import re
from pathlib import Path

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from langchain_community.document_loaders import PyPDFLoader, TextLoader

# 兼容 .docm/.xlsm:宏格式与无宏格式用同一套解析器
_DOCX_SUFFIXES = {".docx", ".docm"}
_XLSX_SUFFIXES = {".xlsx", ".xlsm"}
_MARKDOWN_SUFFIXES = {".md", ".markdown"}


def load_text(file_path: str, file_type: str = "") -> str:
    """把本地文件读成纯文本(按磁盘文件后缀分发)。

    - .pdf  用 PyPDFLoader 提取文字
    - .docx 用 python-docx 顺序抽取(标题→markdown 层级,表格穿插其中)
    - .xlsx 用 openpyxl 逐 sheet/行取值(sheet 名作为标题)
    - .md/.markdown 直接读原始内容;其余文本后缀走通用 TextLoader(保持原行为)
    """
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix in _DOCX_SUFFIXES:
        return _extract_docx(file_path)
    if suffix in _XLSX_SUFFIXES:
        return _extract_xlsx(file_path)
    if suffix in _MARKDOWN_SUFFIXES:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    docs = TextLoader(file_path, encoding="utf-8").load()
    return "\n".join(d.page_content or "" for d in docs)


def _extract_pdf(file_path: str) -> str:
    docs = PyPDFLoader(file_path).load()
    return "\n".join(d.page_content or "" for d in docs)


def _heading_level(paragraph: Paragraph) -> int | None:
    """段落若是标题返回 1-6 的层级,否则 None。兼容中文 Word。

    Word 内建标题的 style_id 恒为 HeadingN(不随界面语言变);再兜底按样式名
    是否含 Heading/标题 判断,层级取样式名里的数字。
    """
    style = paragraph.style
    if style is None:
        return None
    sid = (style.style_id or "").lower()
    m = re.fullmatch(r"heading(\d+)", sid)
    if m:
        return min(int(m.group(1)), 6)
    name = (style.name or "").lower().replace(" ", "")
    for prefix in ("heading", "标题"):
        if name.startswith(prefix):
            tail = name[len(prefix):]
            m = re.match(r"\d+", tail)
            return min(int(m.group(0)), 6) if m else 1
    return None


def _iter_body_blocks(doc: DocxDocument):
    """按文档正文顺序产出 (Paragraph|Table),表格单元格内的嵌套不再展开。"""
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def _table_lines(table: Table) -> list[str]:
    return [" | ".join(cell.text.strip() for cell in row.cells).rstrip(" |") for row in table.rows]


def _extract_docx(file_path: str) -> str:
    doc = DocxDocument(file_path)
    out: list[str] = []
    for block in _iter_body_blocks(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            level = _heading_level(block)
            out.append("#" * level + " " + text if level else text)
        elif isinstance(block, Table):
            out.extend(line for line in _table_lines(block) if line.strip())
    return "\n".join(out)


def _extract_xlsx(file_path: str) -> str:
    from openpyxl import load_workbook

    def sheet_lines(ws) -> list[str]:
        """逐行取值;只在 sheet 有数据时才在其首行前输出 sheet 名标题。"""
        lines: list[str] = []
        heading_emitted = False
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v).strip() for v in row]
            while cells and not cells[-1]:
                cells.pop()  # 裁掉行尾空列
            if not cells:
                continue
            if not heading_emitted:
                if ws.title.strip():
                    lines.append(f"# {ws.title.strip()}")
                heading_emitted = True
            lines.append(" | ".join(cells))
        return lines

    wb = load_workbook(file_path, read_only=True, data_only=True)
    try:
        out: list[str] = []
        for ws in wb.worksheets:
            out.extend(sheet_lines(ws))
        return "\n".join(out)
    finally:
        wb.close()  # 关掉 zip 句柄,否则 Windows 下删除文件会失败
