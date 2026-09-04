from pathlib import Path

from docx import Document

from app.ingestion.loader import load_text
from app.ingestion.splitter import split_sections


def _make_docx(path: Path) -> Path:
    """造一个带 1/2 级标题 + 正文 + 表格的 docx。"""
    doc = Document()
    doc.add_heading("产品介绍", level=1)
    doc.add_paragraph("苹果 价格 是 3000 元")
    doc.add_heading("规格", level=2)
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "名称"
    table.cell(0, 1).text = "价格"
    doc.save(path)
    return path


def test_docx_heading_and_body_and_table(tmp_path):
    path = _make_docx(tmp_path / "产品.docx")
    text = load_text(str(path))
    assert "# 产品介绍" in text
    assert "苹果 价格 是 3000 元" in text
    assert "## 规格" in text
    # 表格按顺序穿插,行内单元格以 | 连接
    assert "名称 | 价格" in text


def test_docx_table_section_path_from_heading(tmp_path):
    path = _make_docx(tmp_path / "产品.docx")
    text = load_text(str(path))
    sections = split_sections(text)
    hit = next(s for s in sections if "名称 | 价格" in s[1])
    # 表格应归属到它前面最近的标题层级:产品介绍 > 规格
    assert hit[0] == "产品介绍 > 规格"


def test_docx_plain_paragraph_without_heading(tmp_path):
    doc = Document()
    doc.add_paragraph("只有一段普通文本 123")
    path = tmp_path / "plain.docx"
    doc.save(path)
    text = load_text(str(path))
    assert "只有一段普通文本 123" in text
    assert not text.lstrip().startswith("#")
