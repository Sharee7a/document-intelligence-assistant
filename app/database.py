import sqlite3
from contextlib import contextmanager
from app.config import DATABASE_PATH


def connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db


@contextmanager
def transaction():
    db = connect()
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize_database():
    with transaction() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, filename TEXT NOT NULL, sha256 TEXT NOT NULL,
            page_count INTEGER NOT NULL, chunk_count INTEGER NOT NULL,
            stored_path TEXT NOT NULL, created_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL,
            page_number INTEGER NOT NULL, text TEXT NOT NULL, bbox TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE)""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)")