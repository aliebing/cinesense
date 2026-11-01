"""The chat agent searches like the results page: films outside the catalogue are found by a live title search."""

from cinesense.api import deps


def test_the_agents_search_service_has_the_live_title_search(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(deps, "get_provider", lambda: "provider")
    monkeypatch.setattr(deps, "get_streaming", lambda: "streaming")
    monkeypatch.setattr(deps, "get_embedder", lambda: None)
    monkeypatch.setattr(deps, "get_live", lambda: sentinel)
    service = deps.agent_search_service()
    assert service.live is sentinel


def test_live_imports_are_enriched_and_the_catalogue_cache_refreshed(monkeypatch):
    calls = []

    class Provider:
        def refresh(self):
            calls.append("refresh")

    import cinesense.ingest.pipeline as pipeline

    monkeypatch.setattr(pipeline, "enrich_new_films", lambda ids: calls.append(("enrich", ids)))
    deps.enrich_live_imports(["imdb-tt0057687"], Provider())
    assert calls == [("enrich", ["imdb-tt0057687"]), "refresh"]


def test_the_agents_search_enriches_its_live_imports_in_the_background(monkeypatch):
    monkeypatch.setattr(deps, "get_provider", lambda: "provider")
    monkeypatch.setattr(deps, "get_streaming", lambda: "streaming")
    monkeypatch.setattr(deps, "get_embedder", lambda: None)
    monkeypatch.setattr(deps, "get_live", lambda: object())
    started = []
    monkeypatch.setattr(deps, "enrich_live_imports", lambda ids, provider: started.append((ids, provider)))
    service = deps.agent_search_service()
    service.on_import(["imdb-tt1"])
    for t in list(__import__("threading").enumerate()):
        if t.name == "enrich-live-imports":
            t.join(2)
    assert started == [(["imdb-tt1"], "provider")]
