from cinesense.chat_agent.tag_matching import resolve_tags

TAGS = ["dark", "space travel", "horror", "medieval", "creepy", "scary", "world war ii", "funny", "gore"]


def test_resolve_exact_synonym_fuzzy_and_unresolved():
    resolved, unresolved = resolve_tags(["Dark", "middle ages", "spooky", "space", "wwii", "darkk", "cozy vibes"], TAGS)
    names = [n for n, _ in resolved]
    assert names == ["dark", "medieval", "creepy", "space travel", "world war ii", "dark"]
    assert all(TAGS[i] == n for n, i in resolved)
    assert unresolved == ["cozy vibes"]


def test_negated_words_never_resolve_to_their_opposite():
    tags = ["romantic", "violent", "funny"]
    resolved, unresolved = resolve_tags(["unromantic", "nonviolent", "not funny"], tags)
    assert resolved == [] and unresolved == ["unromantic", "nonviolent", "not funny"]
