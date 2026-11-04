import sqlite3

import pytest

N_TAGS = 1128


@pytest.fixture
def ml_db(tmp_path):
    """Tiny MovieLens-like SQLite with the movieFinder layout."""
    path = tmp_path / "ml.db"
    c = sqlite3.connect(path)
    c.execute("create table movies (movieId int, title text, genres text, mean real, count int)")
    c.executemany(
        "insert into movies values (?,?,?,?,?)",
        [
            (1, "Matrix, The (1999)", "Action|Sci-Fi", 4.2, 900),
            (2, "Amélie (2001)", "Comedy|Romance", 4.1, 300),
            (3, "Interstellar (2014)", "Sci-Fi|IMAX", 4.3, 1500),
            (4, "No Genome Film (2010)", "Drama", 3.0, 50),
            (5, "Some Documentary (2005)", "Documentary", 3.9, 40),
        ],
    )
    c.execute("create table genome_tags (tagId int, tag text)")
    c.executemany("insert into genome_tags values (?,?)", [(i + 1, f"tag{i + 1}") for i in range(N_TAGS)])
    cols = ", ".join(f'"{i + 1}" real' for i in range(N_TAGS))
    c.execute(f"create table genome_matrix (movieId int, {cols})")
    for mid in (1, 2, 3):
        vals = [0.01] * N_TAGS
        vals[mid] = 0.9  # each film has a distinct strong tag
        c.execute(f"insert into genome_matrix values ({mid}, {', '.join('?' * N_TAGS)})", vals)
    c.commit()
    c.close()
    return path
