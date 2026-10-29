from cinesense.domain.models import Movie, MovieQuery


def _passes(m: Movie, q: MovieQuery, excluded: set[str]) -> bool:
    if q.world_id and q.world_id not in m.world_ids:
        return False
    if q.original_language and m.original_language != q.original_language:
        return False
    if excluded and any(g.lower() in excluded for g in m.genres):
        return False
    if q.max_runtime_min is not None and m.runtime_min is not None and m.runtime_min > q.max_runtime_min:
        return False
    if q.availability == "cinema" and not m.availability.in_cinema_de:
        return False
    if q.availability == "stream" and not m.availability.streaming_flatrate_de:
        return False
    return m.vote_count >= q.min_vote_count


def apply_filters(movies: list[Movie], q: MovieQuery) -> list[Movie]:
    """Deterministic hard filters (spec §7). Unknown runtime is kept rather than excluded."""
    excluded = {g.lower() for g in q.exclude_genres}
    return [m for m in movies if _passes(m, q, excluded)]
