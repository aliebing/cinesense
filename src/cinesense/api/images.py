from cinesense.domain.models import Movie


def with_images(movie: Movie, provider, streaming) -> Movie:
    """Fill posters once per film; afterwards the film is marked checked and costs no further API calls."""
    if streaming is None or not movie.imdb_id or movie.images_checked:
        return movie
    if movie.poster_url and movie.horizontal_poster_url and movie.backdrop_url:
        return movie
    images = streaming.images(movie.imdb_id)
    if images is None:
        return movie  # unknown (budget, outage): try again later
    movie.poster_url = movie.poster_url or images.vertical_poster
    movie.horizontal_poster_url = movie.horizontal_poster_url or images.horizontal_poster
    movie.backdrop_url = movie.backdrop_url or images.horizontal_backdrop
    movie.images_checked = True
    provider.update_images(movie.id, images.vertical_poster, images.horizontal_poster, images.horizontal_backdrop)
    return movie
