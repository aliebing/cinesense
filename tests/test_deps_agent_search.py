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
