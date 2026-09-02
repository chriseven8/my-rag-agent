import io

import pytest
from fastapi.testclient import TestClient

from app.ingestion.keyword_index import KeywordIndex
from app.main import app
from app.retrieval.keyword_channel import KeywordChannel
from app.retrieval.vector_channel import VectorChannel
from app.service.chat_service import ChatService
from app.service.document_service import DocumentService
from tests.conftest import FakeEmbedder, FakeVectorStore


class FakeLLM:
    def invoke(self, messages):
        return type("R", (), {"content": "测试回答"})()


@pytest.fixture
def client(tmp_path):
    store = FakeVectorStore()
    idx = KeywordIndex(":memory:")
    doc_service = DocumentService(upload_dir=str(tmp_path / "uploads"), vector_store=store, keyword_index=idx)
    chat_service = ChatService(
        vector_channel=VectorChannel(store, min_similarity=0.45),
        keyword_channel=KeywordChannel(idx, relative_floor=0.35),
        llm=FakeLLM(),
    )
    app.state.document_service = doc_service
    app.state.chat_service = chat_service
    return TestClient(app)


def test_upload_then_ready(client):
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("手册.md", io.BytesIO("# 第一章\n苹果 价格 是 3000 元".encode()), "text/markdown")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["doc_id"]
    # BackgroundTasks 在响应后执行;轮询几次直到 ready
    for _ in range(20):
        rec = client.get(f"/api/documents/{doc_id}").json()
        if rec["status"] == "ready":
            break
    assert rec["status"] == "ready"


def test_upload_then_chat(client):
    client.post(
        "/api/documents/upload",
        files={"file": ("手册.md", io.BytesIO("# 第一章\n苹果 价格 是 3000 元".encode()), "text/markdown")},
    )
    resp = client.post("/api/chat", json={"query": "苹果 价格"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["no_evidence"] is False
    assert body["references"]


def test_upload_then_delete(client):
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("手册.md", io.BytesIO("内容".encode()), "text/markdown")},
    )
    doc_id = resp.json()["doc_id"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 200
    assert client.get(f"/api/documents/{doc_id}").status_code == 404
