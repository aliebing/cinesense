"""Read films and Tag Genome vectors from movieFinder's MovieLens SQLite (research licence; not committed)."""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

N_TAGS = 1128
_TITLE_RE = re.compile(r"^(.*?)\s*\((\d{4})\)\s*$")
_ARTICLE_RE = re.compile(r"^(.*), (The|A|An|Les|La|Le|L'|Il|Der|Die|Das)$")


@dataclass
class MovieLensFilm:
    movielens_id: int
    title: str
    year: int | None
    genres: list[str]
    ml_rating: float | None
    ml_rating_count: int
    tag_vector: np.ndarray | None  # float32[1128] or None


def parse_title(raw: str) -> tuple[str, int | None]:
    m = _TITLE_RE.match(raw.strip())
    title, year = (m.group(1), int(m.group(2))) if m else (raw.strip(), None)
    a = _ARTICLE_RE.match(title)
    if a:
        sep = "" if a.group(2).endswith("'") else " "
        title = f"{a.group(2)}{sep}{a.group(1)}"
    return title, year


def _genres(raw: str) -> list[str]:
    return [g for g in (raw or "").split("|") if g and g != "(no genres listed)"]


def _connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def read_genome_tags(db_path: Path) -> list[str]:
    with _connect(db_path) as c:
        return [r[0] for r in c.execute("select tag from genome_tags order by tagId")]


def read_films(db_path: Path, min_rating_count: int = 0) -> list[MovieLensFilm]:
    """Films that have a Tag Genome vector, most-rated first."""
    with _connect(db_path) as c:
        cols = ", ".join(f'g."{i + 1}"' for i in range(N_TAGS))
        rows = c.execute(
            f"select m.movieId, m.title, m.genres, m.mean, m.count, {cols} "
            "from movies m join genome_matrix g on g.movieId = m.movieId "
            "where m.count >= ? order by m.count desc, m.movieId",
            (min_rating_count,),
        ).fetchall()
    films = []
    for r in rows:
        title, year = parse_title(r[1])
        films.append(
            MovieLensFilm(
                movielens_id=r[0],
                title=title,
                year=year,
                genres=_genres(r[2]),
                ml_rating=float(r[3]) if r[3] is not None else None,
                ml_rating_count=int(r[4] or 0),
                tag_vector=np.asarray(r[5:], dtype=np.float32),
            )
        )
    return films


def read_documentaries_without_genome(db_path: Path) -> list[MovieLensFilm]:
    with _connect(db_path) as c:
        rows = c.execute(
            "select movieId, title, genres, mean, count from movies "
            "where genres like '%Documentary%' and movieId not in (select movieId from genome_matrix) "
            "order by count desc, movieId"
        ).fetchall()
    out = []
    for r in rows:
        title, year = parse_title(r[1])
        out.append(MovieLensFilm(r[0], title, year, _genres(r[2]), r[3], int(r[4] or 0), None))
    return out
