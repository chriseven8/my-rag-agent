import math
import sqlite3
import threading

import jieba

from ..models import Chunk, DocumentRecord, ScoredChunk

_STOPWORDS = {
    "的", "了", "是", "在", "和", "与", "及", "等", "中", "上", "下",
    "我们", "你们", "他们", "这个", "那个", "一个", "可以", "进行", "以及",
}


class KeywordIndex:
    """自研倒排索引 + BM25(SQLite 持久化)。

    同时承担文档元数据存储(documents 表)与关键词检索(chunks/terms/postings 表)。
    检索单元是 chunk(BM25 里的 N=chunk 数, doclen=chunk 的 token 数)。
    """

    def __init__(self, db_path: str = ":memory:", k1: float = 1.5, b: float = 0.75):
        self.db_path = db_path
        self.k1 = k1
        self.b = b
        if db_path != ":memory:":
            from pathlib import Path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # 入库可能在后台线程(BackgroundTasks/run_in_threadpool)执行,连接须跨线程共用
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # 多线程共享同一连接需串行化访问(sqlite 单连接并发不安全)
        self._lock = threading.RLock()
        self._create_tables()

    # ---- schema ----
    def _create_tables(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents(
                doc_id TEXT PRIMARY KEY,
                doc_name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                error TEXT);
            CREATE TABLE IF NOT EXISTS chunks(
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                section_path TEXT,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                token_count INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS terms(
                term TEXT PRIMARY KEY,
                df INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS postings(
                term TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                tf INTEGER NOT NULL,
                PRIMARY KEY(term, chunk_id));
            """
        )
        self._conn.commit()

    # ---- 分词 ----
    def tokenize(self, text: str) -> list[str]:
        tokens: list[str] = []
        for word in jieba.lcut(text):
            word = word.strip()
            if len(word) < 2:
                continue
            if word in _STOPWORDS:
                continue
            tokens.append(word)
        return tokens

    # ---- 文档元数据 ----
    def upsert_document(self, rec: DocumentRecord) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO documents(doc_id, doc_name, status, created_at, error) VALUES(?,?,?,?,?) "
                "ON CONFLICT(doc_id) DO UPDATE SET status=excluded.status, error=excluded.error",
                (rec.doc_id, rec.doc_name, rec.status.value, rec.created_at, rec.error),
            )
            self._conn.commit()

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
            ).fetchone()
            return self._row_to_record(row) if row else None

    def list_documents(self) -> list[DocumentRecord]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            return [self._row_to_record(r) for r in rows]

    @staticmethod
    def _row_to_record(row) -> DocumentRecord:
        from ..models import DocumentStatus
        return DocumentRecord(
            doc_id=row["doc_id"],
            doc_name=row["doc_name"],
            status=DocumentStatus(row["status"]),
            created_at=row["created_at"],
            error=row["error"],
        )

    def delete_document(self, doc_id: str) -> list[str]:
        with self._lock:
            cur = self._conn.cursor()
            rows = cur.execute("SELECT chunk_id FROM chunks WHERE doc_id=?", (doc_id,)).fetchall()
            chunk_ids = [r["chunk_id"] for r in rows]
            if chunk_ids:
                placeholders = ",".join("?" * len(chunk_ids))
                cur.execute(f"DELETE FROM postings WHERE chunk_id IN ({placeholders})", chunk_ids)
            cur.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
            cur.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
            self._recompute_df(cur)
            self._conn.commit()
            return chunk_ids

    # ---- 建索引 ----
    def add_chunks(self, doc_id: str, chunks: list[Chunk]) -> None:
        with self._lock:
            cur = self._conn.cursor()
            for chunk in chunks:
                tokens = self.tokenize(chunk.text)
                cur.execute(
                    "INSERT OR REPLACE INTO chunks(chunk_id, doc_id, section_path, chunk_index, text, token_count) "
                    "VALUES(?,?,?,?,?,?)",
                    (chunk.chunk_id, chunk.doc_id, chunk.section_path, chunk.chunk_index, chunk.text, len(tokens)),
                )
                tf: dict[str, int] = {}
                for t in tokens:
                    tf[t] = tf.get(t, 0) + 1
                for term, count in tf.items():
                    cur.execute("INSERT INTO terms(term, df) VALUES(?,0) ON CONFLICT(term) DO NOTHING", (term,))
                    cur.execute(
                        "INSERT INTO postings(term, chunk_id, tf) VALUES(?,?,?) "
                        "ON CONFLICT(term, chunk_id) DO UPDATE SET tf=excluded.tf",
                        (term, chunk.chunk_id, count),
                    )
            self._recompute_df(cur)
            self._conn.commit()

    def _recompute_df(self, cur: sqlite3.Cursor) -> None:
        cur.execute(
            "UPDATE terms SET df=(SELECT COUNT(*) FROM postings WHERE postings.term=terms.term)"
        )
        cur.execute("DELETE FROM terms WHERE df=0")

    # ---- BM25 检索 ----
    def bm25_search(self, query: str, top_k: int = 16) -> list[ScoredChunk]:
        tokens = self.tokenize(query)
        if not tokens:
            return []
        with self._lock:
            cur = self._conn.cursor()
            n = cur.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()["c"]
            if n == 0:
                return []
            avgdl = cur.execute("SELECT AVG(token_count) AS a FROM chunks").fetchone()["a"] or 1.0

            scores: dict[str, float] = {}
            for term in set(tokens):
                row = cur.execute("SELECT df FROM terms WHERE term=?", (term,)).fetchone()
                if row is None:
                    continue
                df = row["df"]
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
                postings = cur.execute(
                    "SELECT p.chunk_id, p.tf, c.token_count "
                    "FROM postings p JOIN chunks c ON c.chunk_id=p.chunk_id WHERE p.term=?",
                    (term,),
                ).fetchall()
                for p in postings:
                    dl = p["token_count"] or 0
                    denom = p["tf"] + self.k1 * (1 - self.b + self.b * dl / avgdl)
                    scores[p["chunk_id"]] = scores.get(p["chunk_id"], 0.0) + idf * (
                        p["tf"] * (self.k1 + 1)
                    ) / denom

            if not scores:
                return []
            ranked = sorted(scores, key=lambda cid: -scores[cid])[:top_k]
            results: list[ScoredChunk] = []
            for cid in ranked:
                row = cur.execute(
                    "SELECT c.*, COALESCE(d.doc_name, c.doc_id) AS doc_name "
                    "FROM chunks c LEFT JOIN documents d ON d.doc_id=c.doc_id WHERE c.chunk_id=?",
                    (cid,),
                ).fetchone()
                results.append(ScoredChunk(
                    chunk_id=cid,
                    doc_id=row["doc_id"],
                    doc_name=row["doc_name"],
                    section_path=row["section_path"],
                    text=row["text"],
                    score=scores[cid],
                    channel="keyword",
                ))
            return results
