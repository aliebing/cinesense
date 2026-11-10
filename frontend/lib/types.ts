// Mirrors the backend Pydantic models (backend/cinesense/core/models.py); field names stay snake_case.
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
  title_de?: string | null; // German title from Wikidata (films imported live)
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
  misses?: string[]; // after a widened search: the parts of the original wish this film misses
};

/** A homepage tile: only what the rows need (backend/cinesense/web_api/home.py TILE_FIELDS). */
export type HomeTile = Pick<
  Movie,
  "id" | "title" | "year" | "world_ids" | "youtube_key" | "horizontal_poster_url" | "backdrop_url"
>;

export type HomeData = {
  worlds: MoodWorld[];
  /** per world: its newest top-rated films, then its top classics */
  rows: Record<string, HomeTile[]>;
  /** per world: the ids of its newest top-rated films (the rest of its row are the classics) */
  newest?: Record<string, string[]>;
  newest_from?: number; // the newest are from this year on
  classics_before?: number; // the classics are older than this year
  titles: string[];
};

/** `picked`: the search hits on the homepage, shown larger with a gold frame (the short list). */
export type TileRow = { world: MoodWorld; movies: HomeTile[]; picked?: boolean; featured?: string[]; label?: string }; // featured: ids shown larger; label: the row's heading
