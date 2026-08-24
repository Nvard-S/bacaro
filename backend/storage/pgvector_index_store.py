import psycopg2
from pgvector import Vector
from pgvector.psycopg2 import register_vector

from .interfaces import IndexStore


class PgVectorIndexStore(IndexStore):
    def __init__(self, connection_string):
        self.connection_string = connection_string

    def _connect(self):
        conn = psycopg2.connect(self.connection_string)
        register_vector(conn)
        return conn

    def rebuild(self, ids, embeddings):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM bar_embeddings")
        for place_id, embedding in zip(ids, embeddings):
            cur.execute(
                "INSERT INTO bar_embeddings (place_id, embedding) VALUES (%s, %s)",
                (place_id, Vector(embedding)),
            )
        conn.commit()
        conn.close()

    def count(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM bar_embeddings")
        n = cur.fetchone()[0]
        conn.close()
        return n

    def query(self, embedding, n_results, ids=None):
        conn = self._connect()
        cur = conn.cursor()
        vec = Vector(embedding)
        if ids:
            cur.execute(
                "SELECT place_id FROM bar_embeddings WHERE place_id = ANY(%s) "
                "ORDER BY embedding <=> %s LIMIT %s",
                (list(ids), vec, n_results),
            )
        else:
            cur.execute(
                "SELECT place_id FROM bar_embeddings ORDER BY embedding <=> %s LIMIT %s",
                (vec, n_results),
            )
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows
