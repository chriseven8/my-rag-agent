from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py → parents[2] = 项目根目录(my-rag-agent/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v1"
    chat_model: str = "qwen-plus"
    embedding_mock: bool = True
    embedding_dim: int = 8

    pg_connection_string: str = "postgresql+psycopg2://rag:rag123456@127.0.0.1:5433/rag_db"
    sqlite_path: str = str(PROJECT_ROOT / "data" / "rag.db")

    vector_min_similarity: float = 0.45
    keyword_relative_score_floor: float = 0.35
    rrf_k: int = 60
    vector_top_k: int = 8
    keyword_top_k: int = 8

    evidence_max_total_chars: int = 4000
    evidence_max_snippet_chars: int = 500

    chunk_size: int = 800
    chunk_overlap: int = 120

    llm_mock: bool = True
    llm_temperature: float = 0.5
    # qwen3 系列默认开思考:正文之前先吐一大段 reasoning token,
    # 实测首字延迟从 1.25s 涨到 8.6s,所以默认关掉。None = 不带该参数。
    enable_thinking: bool | None = False

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    frontend_dist: str = str(PROJECT_ROOT / "frontend" / "dist")

    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
