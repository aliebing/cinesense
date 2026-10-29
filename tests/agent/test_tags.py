from cinesense.agent.tags import resolve_tags

TAGS = ["dark", "space travel", "horror", "medieval", "creepy", "scary", "world war ii", "funny", "gore"]


def test_resolve_exact_synonym_fuzzy_and_unresolved():
    resolved, unresolved = resolve_tags(["Dark", "middle ages", "spooky", "space", "wwii", "darkk", "cozy vibes"], TAGS)
    names = [n for n, _ in resolved]
    assert names == ["dark", "medieval", "creepy", "space travel", "world war ii", "dark"]
    assert all(TAGS[i] == n for n, i in resolved)
    assert unresolved == ["cozy vibes"]
