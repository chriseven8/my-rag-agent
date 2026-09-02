from app.ingestion.splitter import split_text


def test_heading_creates_sections():
    text = "# 第一章\n内容一\n\n## 第一节\n内容二"
    chunks = split_text(text, doc_id="d1")
    assert len(chunks) == 2
    assert "第一章" in chunks[0].section_path
    assert "第一节" in chunks[1].section_path


def test_chunk_id_sequential():
    text = "# A\n" + "x" * 100
    chunks = split_text(text, doc_id="d1", chunk_size=50, chunk_overlap=10)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert chunks[0].chunk_id == "d1-0"


def test_long_section_is_split():
    text = "# 大节\n" + ("词语 " * 400)
    chunks = split_text(text, doc_id="d1", chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(c.section_path == "第一章" for c in chunks) is False  # 只是确保有多个 chunk


def test_no_heading_single_section():
    chunks = split_text("纯文本没有标题", doc_id="d1")
    assert len(chunks) == 1
    assert chunks[0].section_path == "文档"
