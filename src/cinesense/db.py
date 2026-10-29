from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector

SCHEMA_PATH = __import__("pathlib").Path(__file__).resolve().parents[2] / "db" / "schema.sql"


@contextmanager
def connect(url: str):
    """Open a Postgres connection with the pgvector adapter registered."""
    with psycopg.connect(url, connect_timeout=15, options="-c search_path=cinesense,public") as conn:
        register_vector(conn)
        yield conn


def init_schema(url: str) -> None:
    with psycopg.connect(url, connect_timeout=15) as conn:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
