from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from .interfaces import BarRepository


class PostgresBarRepository(BarRepository):
    """Assumes the schema already exists -- created via migrations/ and
    run_migrations.py, not by this class. Opens a fresh connection per
    call, same as the SQLite implementation; fine at this app's scale."""

    def __init__(self, connection_string):
        self.connection_string = connection_string

    def _connect(self):
        conn = psycopg2.connect(self.connection_string)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn

    def list_bars(self, neighborhood=None):
        conn = self._connect()
        cur = conn.cursor()
        if neighborhood:
            cur.execute("SELECT * FROM bars WHERE neighborhood = %s", (neighborhood,))
        else:
            cur.execute("SELECT * FROM bars")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_bars_by_ids(self, place_ids):
        if not place_ids:
            return []
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM bars WHERE place_id = ANY(%s)", (list(place_ids),))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def upsert_bar(self, bar):
        """Only touches the columns present in `bar` -- see the SQLite
        implementation's docstring for why that matters."""
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT created_at FROM bars WHERE place_id=%s", (bar["place_id"],))
        existing = cur.fetchone()
        now = datetime.now(timezone.utc).isoformat()
        created_at = existing["created_at"] if existing else now
        cols = [c for c in bar if c != "place_id"]
        all_cols = ["place_id"] + cols + ["created_at", "updated_at"]
        placeholders = ", ".join(["%s"] * len(all_cols))
        col_list = ", ".join(all_cols)
        update_list = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols) + ", updated_at = EXCLUDED.updated_at"
        cur.execute(
            f"""
            INSERT INTO bars ({col_list}) VALUES ({placeholders})
            ON CONFLICT (place_id) DO UPDATE SET {update_list}
            """,
            (bar["place_id"],) + tuple(bar[c] for c in cols) + (created_at, now),
        )
        conn.commit()
        conn.close()

    def update_bar_fields(self, place_id, fields):
        conn = self._connect()
        cur = conn.cursor()
        set_clause = ", ".join(f"{k} = %s" for k in fields) + ", updated_at = %s"
        values = list(fields.values()) + [datetime.now(timezone.utc).isoformat(), place_id]
        cur.execute(f"UPDATE bars SET {set_clause} WHERE place_id = %s", values)
        conn.commit()
        conn.close()

    def bars_missing_content(self, neighborhood=None):
        conn = self._connect()
        cur = conn.cursor()
        where = "website IS NOT NULL AND website != ''"
        params = []
        if neighborhood:
            where += " AND neighborhood = %s"
            params.append(neighborhood)
        cur.execute(
            f"SELECT place_id, website FROM bars WHERE {where} "
            f"AND (cicchetti_content IS NULL OR cicchetti_content = '')",
            params,
        )
        rows = [dict(r) for r in cur.fetchall()]
        cur.execute(
            f"SELECT COUNT(*) AS n FROM bars WHERE {where} "
            f"AND cicchetti_content IS NOT NULL AND cicchetti_content != ''",
            params,
        )
        skipped = cur.fetchone()["n"]
        conn.close()
        return rows, skipped

    def bars_missing_tags(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM bars WHERE tags IS NULL OR tags = '' OR blurb IS NULL")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def bars_missing_instagram(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM bars WHERE website IS NOT NULL AND website != '' "
            "AND (instagram_url IS NULL OR instagram_url = '')"
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def log_search(self, entry):
        # created_at uses the table's now() default.
        cols = ["query", "neighborhood", "tags", "mode", "analyzed",
                "answer", "results", "location_detected", "geo_filter_applied"]
        conn = self._connect()
        cur = conn.cursor()
        placeholders = ", ".join(["%s"] * len(cols))
        cur.execute(
            f"INSERT INTO search_logs ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(entry.get(c) for c in cols),
        )
        conn.commit()
        conn.close()
