/** Search-engine and link-preview texts. The world entries mirror backend/cinesense/core/worlds.py (ids, titles);
 *  they are static so metadata, sitemap and preview images need no API call. */

export const SITE_URL = "https://cinesense.de";
export const SITE_NAME = "CineSense";
export const SITE_TITLE = "CineSense: find a film by mood";
export const SITE_DESCRIPTION =
  "Don't choose a movie. Choose a feeling. Tell CineSense how you want to feel and it finds films to stream in " +
  "Germany or see in cinemas, with reasons from real catalogue data (MovieLens, Wikidata, Wikipedia).";

export type WorldSeo = { id: string; title: string; about: string };

export const WORLD_SEO: WorldSeo[] = [
  { id: "suspense", title: "Suspense & Mystery", about: "mystery films and thrillers full of secrets and twists" },
  { id: "scifi", title: "Science Fiction", about: "science fiction films about space, the future and wonder" },
  { id: "romance", title: "Love & Feelings", about: "romantic and emotional films" },
  { id: "adventure", title: "Adventure", about: "adventure films with epic journeys and discovery" },
  { id: "comedy", title: "Comedy & Feel-Good", about: "funny, relaxed comedies and feel-good films" },
  { id: "action", title: "Action & Adrenaline", about: "action films with pace, explosions and heroes" },
];

export const worldSeo = (id: string) => WORLD_SEO.find((w) => w.id === id);
