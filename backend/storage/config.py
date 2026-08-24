"""Picks which storage backend to build, based on the DATA_BACKEND
environment variable. Explicit rather than automatic -- the app won't
switch to Postgres just because DATABASE_URL happens to be set."""
import os

from .chroma_index_store import ChromaIndexStore
from .pgvector_index_store import PgVectorIndexStore
from .postgres_repository import PostgresBarRepository
from .sqlite_repository import SqliteBarRepository


def _database_url():
    url = (os.environ.get("DATABASE_URL") or "").strip()
    # Tolerate a common paste mistake: the whole "DATABASE_URL=..." line (or a
    # value wrapped in quotes) pasted into the value field. Normalize it so a
    # stray prefix or quotes don't break the connection.
    if url.lower().startswith("database_url="):
        url = url.split("=", 1)[1].strip()
    if len(url) >= 2 and url[0] == url[-1] and url[0] in "\"'":
        url = url[1:-1].strip()
    if not url:
        raise RuntimeError("DATA_BACKEND=postgres requires DATABASE_URL to be set in .env")
    return url


def get_repository(app_dir):
    backend = os.environ.get("DATA_BACKEND", "sqlite")
    if backend == "postgres":
        return PostgresBarRepository(_database_url())
    return SqliteBarRepository(os.path.join(app_dir, "venice_bars.db"))


def get_index_store(app_dir):
    backend = os.environ.get("DATA_BACKEND", "sqlite")
    if backend == "postgres":
        return PgVectorIndexStore(_database_url())
    return ChromaIndexStore(os.path.join(app_dir, "chroma_db"))
