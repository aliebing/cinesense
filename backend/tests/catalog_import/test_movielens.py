from cinesense.catalog_import.movielens import parse_title, read_films, read_genome_tags


def test_parse_title_moves_article_and_extracts_year():
    assert parse_title("Matrix, The (1999)") == ("The Matrix", 1999)
    assert parse_title("Amélie (2001)") == ("Amélie", 2001)
    assert parse_title("Untitled") == ("Untitled", None)


def test_read_genome_tags_in_column_order(ml_db):
    tags = read_genome_tags(ml_db)
    assert len(tags) == 1128 and tags[0] == "tag1"


def test_read_films_only_genome_ordered_by_count(ml_db):
    films = read_films(ml_db)
    assert [f.movielens_id for f in films] == [3, 1, 2]
    matrix = films[1]
    assert matrix.title == "The Matrix" and matrix.year == 1999
    assert matrix.genres == ["Action", "Sci-Fi"]
    assert matrix.tag_vector.shape == (1128,) and matrix.tag_vector[1] > 0.8


def test_read_documentaries_without_genome(ml_db):
    from cinesense.catalog_import.movielens import read_documentaries_without_genome

    docs = read_documentaries_without_genome(ml_db)
    assert [d.movielens_id for d in docs] == [5]
    assert docs[0].tag_vector is None
