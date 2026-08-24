"""Apply any .sql files in migrations/ that haven't run against DATABASE_URL
yet, in filename order. Keeps a record of what's been applied in a
schema_migrations table, so this is safe to run repeatedly.
"""
import os
import psycopg2
from dotenv import load_dotenv

APP_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(APP_DIR, ".env"))

DATABASE_URL = os.environ.get("DATABASE_URL")
MIGRATIONS_DIR = os.path.join(APP_DIR, "migrations")


def main():
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is not set in .env")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            conn.commit()

            cur.execute("SELECT filename FROM schema_migrations")
            already_applied = {row[0] for row in cur.fetchall()}

        for filename in sorted(os.listdir(MIGRATIONS_DIR)):
            if not filename.endswith(".sql") or filename in already_applied:
                continue
            path = os.path.join(MIGRATIONS_DIR, filename)
            with open(path) as f:
                sql = f.read()
            print(f"Applying {filename}...")
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (filename,),
                )
            conn.commit()
            print(f"  done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
