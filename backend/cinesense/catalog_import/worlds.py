"""Recompute every film's mood worlds (and its main world first) in the catalogue, after the genre-to-world mapping
changed. Takes a few minutes for the whole catalogue.

    cd backend && uv run --env-file ../.env python -m cinesense.catalog_import.worlds
"""

import logging

import numpy as np

from cinesense.core.config import get_settings
from cinesense.core.worlds_map import assign_worlds, world_scores
from cinesense.data_sources.db import connect

log = logging.getLogger(__name__)
BATCH = 500


def reassign(url: str) -> tuple[int, int]:
    """Every film's world_ids from its genres and tag vector; returns (films, changed)."""
    with connect(url) as conn:
        tags = [r[0] for r in conn.execute("select tag from genome_tags order by idx")]
        rows = conn.execute("select id, genres, top_tags, tag_vector, world_ids from films").fetchall()
        changed = []
        for fid, genres, top, vector, old in rows:
            v = None
            if vector is not None:
                v = np.asarray(vector.to_numpy() if hasattr(vector, "to_numpy") else vector, dtype=np.float32)
            new = assign_worlds(list(genres or []), list(top or []), world_scores(v, tags))
            if new != list(old or []):
                changed.append((new, fid))
        with conn.cursor() as cur:
            for i in range(0, len(changed), BATCH):
                cur.executemany("update films set world_ids = %s where id = %s", changed[i : i + BATCH])
        conn.commit()
    return len(rows), len(changed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    total, n = reassign(get_settings().database_url)
    print(f"{n} of {total} films got new worlds")
