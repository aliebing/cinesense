// Mirrors the backend Pydantic models (src/cinesense/domain/models.py); field names stay snake_case.
export type Availability = {
  in_cinema_de: boolean;
  streaming_flatrate_de: string[];
};

export type Movie = {
  id: string;
  title: string;
  year: number | null;
  runtime_min: number | null;
  original_language: string;
  genres: string[];
  world_ids: string[];
  overview: string;
  poster_url: string | null;
  backdrop_url: string | null;
  youtube_key: string | null;
  vote_average: number | null;
  vote_count: number;
  age_rating_de: string | null;
  availability: Availability;
  is_placeholder: boolean;
};

export type MoodWorld = {
  id: string;
  title_de: string;
  kicker: string;
  subtitle_de: string;
  tint: string;
  genres: string[];
};

export type RankedMovie = {
  movie: Movie;
  score: number;
  match_percent: number;
};

export type HomeData = {
  worlds: MoodWorld[];
  tiles: Movie[];
  titles: string[];
};
