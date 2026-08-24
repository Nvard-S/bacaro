import sqlite3
from datetime import datetime, timezone

from .interfaces import BarRepository


class SqliteBarRepository(BarRepository):
    def __init__(self, db_path):
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bars (
                place_id TEXT PRIMARY KEY,
                name TEXT,
                address TEXT,
                rating REAL,
                user_rating_count INTEGER,
                website TEXT,
                place_types TEXT,
                primary_type TEXT,
                latitude REAL,
                longitude REAL,
                neighborhood TEXT,
                reviews TEXT,
                found_via_query TEXT,
                cicchetti_content TEXT,
                price_level TEXT,
                price_range_min REAL,
                price_range_max REAL,
                price_range_currency TEXT,
                tags TEXT,
                blurb TEXT,
                instagram_url TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(bars)").fetchall()]
        for col, coltype in [
            ("price_level", "TEXT"), ("price_range_min", "REAL"),
            ("price_range_max", "REAL"), ("price_range_currency", "TEXT"),
            ("tags", "TEXT"), ("blurb", "TEXT"), ("instagram_url", "TEXT"),
        ]:
            if col not in cols:
                conn.execute(f"ALTER TABLE bars ADD COLUMN {col} {coltype}")
        conn.commit()
        conn.close()

    def list_bars(self, neighborhood=None):
        conn = self._connect()
        if neighborhood:
            rows = conn.execute(
                "SELECT * FROM bars WHERE neighborhood = ?", (neighborhood,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM bars").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_bars_by_ids(self, place_ids):
        if not place_ids:
            return []
        conn = self._connect()
        placeholders = ",".join("?" * len(place_ids))
        rows = conn.execute(
            f"SELECT * FROM bars WHERE place_id IN ({placeholders})", place_ids
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def upsert_bar(self, bar):
        """Only touches the columns present in `bar` -- any column not
        included (e.g. cicchetti_content/tags/blurb/instagram_url when
        called from collection) is left exactly as-is on conflict, and
        defaults to NULL on a brand-new row. This matters: it's what lets
        re-running collection refresh ratings/hours without erasing tags
        or scraped content a later step already filled in."""
        conn = self._connect()
        existing = conn.execute(
            "SELECT created_at FROM bars WHERE place_id=?", (bar["place_id"],)
        ).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        created_at = existing["created_at"] if existing else now
        cols = [c for c in bar if c != "place_id"]
        all_cols = ["place_id"] + cols + ["created_at", "updated_at"]
        placeholders = ",".join("?" * len(all_cols))
        col_list = ", ".join(all_cols)
        update_list = ", ".join(f"{c}=excluded.{c}" for c in cols) + ", updated_at=excluded.updated_at"
        conn.execute(
            f"""
            INSERT INTO bars ({col_list}) VALUES ({placeholders})
            ON CONFLICT(place_id) DO UPDATE SET {update_list}
            """,
            (bar["place_id"],) + tuple(bar[c] for c in cols) + (created_at, now),
        )
        conn.commit()
        conn.close()

    def update_bar_fields(self, place_id, fields):
        conn = self._connect()
        set_clause = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
        values = list(fields.values()) + [datetime.now(timezone.utc).isoformat(), place_id]
        conn.execute(f"UPDATE bars SET {set_clause} WHERE place_id=?", values)
        conn.commit()
        conn.close()

    def bars_missing_content(self, neighborhood=None):
        conn = self._connect()
        where = "website IS NOT NULL AND website != ''"
        params = ()
        if neighborhood:
            where += " AND neighborhood = ?"
            params = (neighborhood,)
        rows = conn.execute(
            f"SELECT place_id, website FROM bars WHERE {where} "
            f"AND (cicchetti_content IS NULL OR cicchetti_content = '')",
            params,
        ).fetchall()
        skipped = conn.execute(
            f"SELECT COUNT(*) FROM bars WHERE {where} "
            f"AND cicchetti_content IS NOT NULL AND cicchetti_content != ''",
            params,
        ).fetchone()[0]
        conn.close()
        return [dict(r) for r in rows], skipped

    def bars_missing_tags(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM bars WHERE tags IS NULL OR tags = '' OR blurb IS NULL"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def bars_missing_instagram(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM bars WHERE website IS NOT NULL AND website != '' "
            "AND (instagram_url IS NULL OR instagram_url = '')"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
