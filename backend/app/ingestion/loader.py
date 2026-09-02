from langchain_community.document_loaders import PyPDFLoader, TextLoader


def load_text(file_path: str, file_type: str = "") -> str:
    """把本地文件读成纯文本。pdf 用 PyPDFLoader;md/txt 直接读。"""
    file_type = (file_type or "").lower()
    if "pdf" in file_type:
        docs = PyPDFLoader(file_path).load()
        return "\n".join(d.page_content or "" for d in docs)
    if "md" in file_type or "markdown" in file_type:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    docs = TextLoader(file_path, encoding="utf-8").load()
    return "\n".join(d.page_content or "" for d in docs)
