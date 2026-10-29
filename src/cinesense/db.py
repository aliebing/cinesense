from contextlib import contextmanager
from pathlib import Path
from threading import Lock

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"
_pools: dict[str, ConnectionPool] = {}
_lock = Lock()


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)
    conn.commit()


def get_pool(url: str) -> ConnectionPool:
    """One shared pool per database URL (Supabase connections are expensive to open)."""
    with _lock:
        pool = _pools.get(url)
        if pool is None:
            pool = ConnectionPool(
                url,
                min_size=1,
                max_size=8,
                kwargs={"connect_timeout": 15, "options": "-c search_path=cinesense,public"},
                configure=_configure,
                open=True,
            )
            _pools[url] = pool
        return pool


@contextmanager
def connect(url: str):
    """A pooled Postgres connection with the pgvector adapter and the cinesense search_path."""
    with get_pool(url).connection() as conn:
        yield conn


def init_schema(url: str) -> None:
    with psycopg.connect(url, connect_timeout=15) as conn:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
