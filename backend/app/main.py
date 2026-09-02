from fastapi import FastAPI

from .config import get_settings

app = FastAPI(title="my-rag-agent")
get_settings()  # 提前加载 .env,配置错误尽早暴露


@app.get("/api/health")
def health():
    return {"status": "ok"}
