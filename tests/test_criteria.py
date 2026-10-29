import pytest
from pydantic import ValidationError

from cinesense.domain.criteria import SearchCriteria, TagCriterion


def test_tag_weight_range_and_count():
    with pytest.raises(ValidationError):
        TagCriterion(idx=1, weight=0)
    with pytest.raises(ValidationError):
        TagCriterion(idx=1, weight=11)
    with pytest.raises(ValidationError):
        SearchCriteria(tags=[TagCriterion(idx=i) for i in range(13)])


def test_tag_partitions():
    c = SearchCriteria(
        tags=[
            TagCriterion(idx=1, weight=8),
            TagCriterion(idx=2, mode="must"),
            TagCriterion(idx=3, mode="not"),
        ]
    )
    assert c.prefer_weights() == {1: 8, 2: 5}
    assert c.must_tags() == [2] and c.not_tags() == [3]
    assert c.has_tags() and not c.has_text_signal()


def test_with_no_horror_adds_genre_and_tag():
    c = SearchCriteria().with_no_horror(horror_idx=7)
    assert "Horror" in c.exclude_genres
    assert c.not_tags() == [7]
    assert c.with_no_horror(horror_idx=7).not_tags() == [7]  # idempotent
