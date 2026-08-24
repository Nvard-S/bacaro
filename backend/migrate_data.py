"""One-off data migration: copy every row from the local SQLite database
into Supabase, and copy the embeddings already stored in the local ChromaDB
folder into the new bar_embeddings table (no need to re-call OpenAI).

Safe to re-run: uses upserts, so running it twice just overwrites with the
same data instead of creating duplicates.
"""
import os
import sqlite3

import chromadb
import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

APP_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(APP_DIR, ".env"))

DB_PATH = os.path.join(APP_DIR, "venice_bars.db")
CHROMA_PATH = os.path.join(APP_DIR, "chroma_db")
BARS_COLLECTION_NAME = "bars"
DATABASE_URL = os.environ.get("DATABASE_URL")

BAR_COLUMNS = [
    "place_id", "name", "address", "rating", "user_rating_count", "website",
    "place_types", "primary_type", "latitude", "longitude", "neighborhood",
    "reviews", "found_via_query", "cicchetti_content", "price_level",
    "price_range_min", "price_range_max", "price_range_currency", "tags",
    "blurb", "instagram_url", "created_at", "updated_at",
]


def migrate_bars(pg_conn):
    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    rows = sqlite_conn.execute("SELECT * FROM bars").fetchall()
    sqlite_conn.close()

    placeholders = ", ".join(["%s"] * len(BAR_COLUMNS))
    col_list = ", ".join(BAR_COLUMNS)
    update_list = ", ".join(f"{c} = EXCLUDED.{c}" for c in BAR_COLUMNS if c != "place_id")
    sql = f"""
        INSERT INTO bars ({col_list}) VALUES ({placeholders})
        ON CONFLICT (place_id) DO UPDATE SET {update_list}
    """
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(sql, tuple(row[c] for c in BAR_COLUMNS))
    pg_conn.commit()
    return len(rows)


def migrate_embeddings(pg_conn):
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        collection = chroma_client.get_collection(BARS_COLLECTION_NAME)
    except Exception:
        return 0

    data = collection.get(include=["embeddings"])
    ids = data["ids"]
    embeddings = data["embeddings"]

    with pg_conn.cursor() as cur:
        for place_id, embedding in zip(ids, embeddings):
            cur.execute(
                """
                INSERT INTO bar_embeddings (place_id, embedding) VALUES (%s, %s)
                ON CONFLICT (place_id) DO UPDATE SET embedding = EXCLUDED.embedding
                """,
                (place_id, embedding),
            )
    pg_conn.commit()
    return len(ids)


def main():
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is not set in .env")

    pg_conn = psycopg2.connect(DATABASE_URL)
    register_vector(pg_conn)
    try:
        bar_count = migrate_bars(pg_conn)
        print(f"Migrated {bar_count} bars.")
        embedding_count = migrate_embeddings(pg_conn)
        print(f"Migrated {embedding_count} embeddings.")
    finally:
        pg_conn.close()


if __name__ == "__main__":
    main()
