-- CineSense catalogue schema (Supabase Postgres + pgvector). Idempotent.
-- Lives in its own schema because the Supabase database is shared with other projects.
create extension if not exists vector;
create extension if not exists pg_trgm;
create extension if not exists unaccent;
create extension if not exists fuzzystrmatch;
create schema if not exists cinesense;
set search_path to cinesense, public;

-- unaccent() is not immutable; wrap it so it can be used in indexes
create or replace function cs_norm(t text) returns text
  language sql immutable parallel safe as $$ select lower(public.unaccent('public.unaccent', coalesce(t, ''))) $$;

create table if not exists films (
  id text primary key,                 -- "ml-<movieId>" or "wd-<QID>"
  movielens_id int unique,
  wikidata_id text unique,
  imdb_id text,
  kind text not null default 'film',   -- film | documentary
  title text not null,
  year int,
  runtime_min int,
  original_language text,
  genres text[] not null default '{}',
  directors text[] not null default '{}',
  cast_top text[] not null default '{}',
  world_ids text[] not null default '{}',
  top_tags text[] not null default '{}',
  youtube_key text,
  release_date_de date,
  wikipedia_title text,
  overview text not null default '',
  ml_rating real,
  ml_rating_count int not null default 0,
  poster_url text,
  horizontal_poster_url text,
  backdrop_url text,
  images_fetched_at timestamptz,
  tag_vector vector(1128)
);
create index if not exists films_title_trgm on films using gin (cs_norm(title) gin_trgm_ops);
create index if not exists films_imdb on films (imdb_id);
create index if not exists films_worlds on films using gin (world_ids);

create table if not exists film_people (
  film_id text not null references films(id) on delete cascade,
  name text not null,
  role text not null,                  -- cast | director
  ord int not null,
  primary key (film_id, role, ord)
);
create index if not exists film_people_name_trgm on film_people using gin (cs_norm(name) gin_trgm_ops);

create table if not exists plot_chunks (
  film_id text not null references films(id) on delete cascade,
  idx int not null,
  text text not null,
  embedding vector(1536) not null,
  primary key (film_id, idx)
);
create index if not exists plot_chunks_hnsw on plot_chunks using hnsw (embedding vector_cosine_ops);

create table if not exists genome_tags (idx int primary key, tag text not null);

create table if not exists streaming_cache (imdb_id text primary key, payload jsonb not null, fetched_at timestamptz not null);
create table if not exists browse_cache (key text primary key, payload jsonb not null, fetched_at timestamptz not null);
create table if not exists api_budget (month text primary key, calls int not null default 0);
create table if not exists trailer_cache (film_id text primary key, video_id text, checked_at timestamptz not null);
create table if not exists youtube_quota (day date primary key, calls int not null default 0);
