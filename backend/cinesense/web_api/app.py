"""The FastAPI app: catalogue, search and world endpoints; chat, inspect and taste come from their own routers."""

import logging
import threading
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cinesense.core.config import load_env_file
from cinesense.core.criteria import SearchCriteria
from cinesense.core.models import MoodWorld, Movie, RankedMovie
from cinesense.core.worlds import WORLDS, get_world
from cinesense.search import widening
from cinesense.search.service import SearchService
from cinesense.web_api.admin import router as admin_router
from cinesense.web_api.admin_session import router as admin_session_router
from cinesense.web_api.chat import router as chat_router
from cinesense.web_api.deps import (
    get_embedder,
    get_live,
    get_provider,
    get_streaming,
    get_trailer_checker,
    get_trailers,
)
from cinesense.web_api.eval_view import router as eval_router
from cinesense.web_api.home import HomeCache, build_home, row_trailers
from cinesense.web_api.images import with_images as _with_images
from cinesense.web_api.inspect import router as inspect_router
from cinesense.web_api.taste import UserProfile, get_user
from cinesense.web_api.taste import router as taste_router

Provider = Annotated[object, Depends(get_provider)]
Streaming = Annotated[object, Depends(get_streaming)]
Embedder = Annotated[object, Depends(get_embedder)]
Live = Annotated[object, Depends(get_live)]
Trailers = Annotated[object, Depends(get_trailers)]
Checker = Annotated[object, Depends(get_trailer_checker)]

IMAGE_FILL = 12  # images fetched per list response (each new film costs one Streaming API request once)
RELATED_IMAGE_FILL = 24  # the related row shows up to 24 films; no blank tiles
TRAILER_FILL = 4  # top search hits without a Wikidata trailer ask YouTube (cached 30 days; 95 searches/day)


class DiscoverRequest(BaseModel):
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=50)
    fill_images: bool = True  # False: no Streaming API image lookups or YouTube searches (homepage background rows)
    relaxed_from: SearchCriteria | None = None  # the user widened this search: mark what each film misses of it


class RelaxationOut(BaseModel):
    id: str
    label: str
    count: int
    criteria: SearchCriteria


class DiscoverResponse(BaseModel):
    items: list[RankedMovie]
    total: int
    hidden_by_exclusion: int = 0
    extended_used: bool = False
    corrected_person: str | None = None  # autocorrect: the person / title a misspelt search found
    corrected_title: str | None = None
    hidden_by: dict[str, int] = Field(default_factory=dict)  # per exclusion ("genre:Horror", "tag:284"): films hidden
    total_capped: bool = False  # total is a lower bound: the mood search kept only its best films ("500+")
    relaxations: list[RelaxationOut] = Field(default_factory=list)  # ways to widen a thin search (/api/search)


def create_app(load_env: bool = True) -> FastAPI:
    """`load_env` is the real server: it also warms the catalogue and the homepage at startup (tests skip both)."""
    if load_env:
        load_env_file()
    home_cache = HomeCache()

    def warm() -> None:
        try:
            home_cache.get(lambda: build_home(get_provider(), get_streaming(), get_trailer_checker(), get_trailers()))
        except Exception:  # noqa: BLE001 — the first visitor then builds it
            logging.getLogger(__name__).exception("warming the homepage failed")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if load_env:
            threading.Thread(target=warm, daemon=True).start()  # the catalogue load takes seconds
        yield

    app = FastAPI(title="CineSense API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,  # local dev: the admin session cookie crosses from :3000 to :8000
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(inspect_router)
    app.include_router(eval_router)
    app.include_router(admin_session_router)
    app.include_router(admin_router)
    app.include_router(taste_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/worlds")
    def worlds() -> list[MoodWorld]:
        return list(WORLDS)

    @app.get("/api/suggest")
    def suggest(
        provider: Provider,
        field: Literal["title", "person"],
        q: Annotated[str, Query(max_length=100)] = "",
        role: Literal["any", "cast", "director"] = "any",
    ) -> list[dict]:
        """Suggestions while typing in the advanced search (catalogue only, typo-tolerant); the UI applies a
        title or person only when one is picked."""
        q = q.strip()
        if len(q) < 3:
            return []
        if field == "person":
            return [{"value": n, "label": n} for n in provider.suggest_people(q, role)]
        out, seen = [], set()
        for fid in provider.search_title(q, limit=12):
            m = provider.get_movie(fid)
            if m is None or m.title in seen:
                continue
            seen.add(m.title)
            out.append({"value": m.title, "label": f"{m.title} ({m.year})" if m.year else m.title})
        return out[:8]

    @app.get("/api/tags")
    def tags(provider: Provider) -> list[dict]:
        return [{"idx": i, "tag": t} for i, t in enumerate(provider.list_tags())]

    def _discover(
        req: DiscoverRequest,
        provider,
        streaming,
        embedder,
        live=None,
        tasks=None,
        profile=None,
        checker=None,
        trailers=None,
        search_trailers=True,
    ) -> DiscoverResponse:
        res = SearchService(provider, streaming, embedder, live).run(req.criteria, req.offset, req.limit, profile)
        row_trailers([r.movie for r in res.items], checker, trailers)
        if trailers is not None and search_trailers:  # the search rows play trailers on hover: the best hits need one
            top = [r.movie for r in res.items[:TRAILER_FILL] if r.movie.youtube_key is None]
            with ThreadPoolExecutor(max_workers=TRAILER_FILL) as pool:  # uncached ids cost a round trip each
                keys = list(pool.map(lambda m: trailers.find_trailer(m.id, m.title, m.year), top))
            for m, key in zip(top, keys, strict=True):
                m.youtube_key = key
            if checker is not None and top:
                checker.filter_known(top)  # a reported fallback trailer is never offered again
        for r in res.items[: IMAGE_FILL if req.fill_images else 0]:
            _with_images(r.movie, provider, streaming)
        if res.extended_used and tasks is not None:
            from cinesense.web_api.deps import enrich_live_imports

            new_ids = [r.movie.id for r in res.items if r.movie.id.startswith(("wd-", "imdb-"))]
            tasks.add_task(enrich_live_imports, new_ids, provider)
        return DiscoverResponse(
            items=res.items,
            total=res.total,
            hidden_by_exclusion=res.hidden_by_exclusion,
            extended_used=res.extended_used,
            corrected_person=res.corrected_person,
            corrected_title=res.corrected_title,
            hidden_by=res.hidden_by,
            total_capped=res.total_capped,
        )

    @app.post("/api/discover")
    def discover(
        req: DiscoverRequest,
        provider: Provider,
        streaming: Streaming,
        embedder: Embedder,
        profile: UserProfile,
        checker: Checker,
        trailers: Trailers,
    ) -> DiscoverResponse:
        # background rows (fill_images=False) spend no API budget: no images, no YouTube search (the cache is free)
        return _discover(
            req,
            provider,
            streaming,
            embedder,
            profile=profile,
            checker=checker,
            trailers=trailers,
            search_trailers=req.fill_images,
        )

    @app.post("/api/search")
    def search(
        req: DiscoverRequest,
        provider: Provider,
        streaming: Streaming,
        embedder: Embedder,
        live: Live,
        tasks: BackgroundTasks,
        profile: UserProfile,
        checker: Checker,
        trailers: Trailers,
    ) -> DiscoverResponse:
        res = _discover(req, provider, streaming, embedder, live, tasks, profile, checker, trailers)
        if req.relaxed_from is not None:
            widening.mark_misses(res.items, req.relaxed_from, provider)
        if req.offset == 0 and res.total < widening.MIN_RESULTS:
            # probes never use the Streaming API or the live search
            probe_service = SearchService(provider, None, embedder)
            options = widening.probe(probe_service, req.criteria, provider.list_tags(), res.total)
            res.relaxations = [
                RelaxationOut(id=o.id, label=o.label, count=o.count, criteria=o.criteria) for o in options
            ]
        return res

    @app.get("/api/worlds/{world_id}/movies")
    def world_movies(
        world_id: str,
        provider: Provider,
        profile: UserProfile,
        checker: Checker,
        trailers: Trailers,
        limit: Annotated[int, Query(ge=1, le=100)] = 12,
    ) -> list[RankedMovie]:
        if get_world(world_id) is None:
            raise HTTPException(status_code=404, detail="world_not_found")
        # with the profile: a rejected film never comes back as the world's default stage film
        items = SearchService(provider).run(SearchCriteria(world_id=world_id), 0, limit, profile).items
        row_trailers([r.movie for r in items], checker, trailers)
        return items

    @app.get("/api/movies/{movie_id}")
    def movie(movie_id: str, provider: Provider, streaming: Streaming, trailers: Trailers, checker: Checker) -> Movie:
        found = provider.get_movie(movie_id)
        if found is None:
            raise HTTPException(status_code=404, detail="movie_not_found")
        if checker is not None:
            checker.filter_playable([found])
        if found.youtube_key is None and trailers is not None:  # Wikidata trailer ids win when they play
            found.youtube_key = trailers.find_trailer(found.id, found.title, found.year)
            if checker is not None:
                checker.filter_playable([found])  # a reported fallback trailer is never offered again
        if streaming is not None and found.imdb_id:
            found.availability.streaming_de = streaming.get_de(found.imdb_id)
        return _with_images(found, provider, streaming)

    @app.get("/api/movies/{movie_id}/related")
    def related(
        movie_id: str,
        provider: Provider,
        streaming: Streaming,
        profile: UserProfile,
        checker: Checker,
        trailers: Trailers,
        limit: Annotated[int, Query(ge=1, le=100)] = 13,
        world_id: str | None = None,
    ) -> list[RankedMovie]:
        found = provider.get_movie(movie_id)
        if found is None:
            raise HTTPException(status_code=404, detail="movie_not_found")
        # Rank within the world the user is browsing; fall back to the film's first world.
        if world_id is None or get_world(world_id) is None:
            world_id = found.world_ids[0] if found.world_ids else None
        items = SearchService(provider).run(SearchCriteria(world_id=world_id), 0, limit + 1, profile).items
        items = [r for r in items if r.movie.id != movie_id][:limit]
        row_trailers([r.movie for r in items], checker, trailers)
        for r in items[:RELATED_IMAGE_FILL]:
            _with_images(r.movie, provider, streaming)
        return items

    class TrailerReport(BaseModel):
        video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{6,20}$")

    @app.post("/api/trailers/report", status_code=204)
    def report_trailer(
        req: TrailerReport, checker: Checker, provider: Provider, user: Annotated[str | None, Depends(get_user)]
    ) -> None:
        """The embedded player could not play this trailer (deleted, blocked in Germany, embedding off)."""
        if user is None:
            raise HTTPException(status_code=400, detail="missing_user_id")
        if checker is None:
            return
        known = checker.served(req.video_id) or any(m.youtube_key == req.video_id for m in provider.list_movies())
        if not known:
            raise HTTPException(status_code=404, detail="unknown_trailer")
        if not checker.report(req.video_id, user, known=True):
            raise HTTPException(status_code=429, detail="too_many_reports")

    @app.get("/api/home")
    def home(provider: Provider, streaming: Streaming, checker: Checker, trailers: Trailers) -> dict:
        return home_cache.get(lambda: build_home(provider, streaming, checker, trailers))

    return app
