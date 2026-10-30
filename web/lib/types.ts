// Mirrors the backend Pydantic models (src/cinesense/domain/models.py); field names stay snake_case.
export type StreamingOption = {
  service: string;
  type: "subscription" | "rent" | "buy" | "addon" | "free";
  link: string | null;
};

export type Availability = {
  in_cinema_de: boolean;
  /** null = unknown; [] = known not streaming */
  streaming_de: StreamingOption[] | null;
  subscription_services: string[];
};

export type Movie = {
  id: string;
  title: string;
  kind: "film" | "documentary";
  year: number | null;
  runtime_min: number | null;
  original_language: string | null;
  genres: string[];
  world_ids: string[];
  top_tags: string[];
  overview: string;
  directors: string[];
  cast_top: string[];
  movielens_id: number | null;
  imdb_id: string | null;
  wikidata_id: string | null;
  wikipedia_title: string | null;
  release_date_de: string | null;
  poster_url: string | null;
  horizontal_poster_url: string | null;
  backdrop_url: string | null;
  youtube_key: string | null;
  ml_rating: number | null;
  ml_rating_count: number;
  availability: Availability;
  is_placeholder: boolean;
};

export type MoodWorld = {
  id: string;
  title: string;
  kicker: string;
  subtitle: string;
  tint: string;
  genres: string[];
};

export type RankedMovie = {
  movie: Movie;
  score: number;
  match_percent: number;
  reasons: string[];
};

export type HomeData = {
  worlds: MoodWorld[];
  rows: Record<string, Movie[]>;
  tiles: Movie[];
  titles: string[];
};

/** `picked`: the search hits on the homepage, shown larger with a gold frame (the short list). */
export type TileRow = { world: MoodWorld; movies: Movie[]; picked?: boolean };
