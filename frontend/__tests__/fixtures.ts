import type { HomeData, Movie, MoodWorld, RankedMovie } from "@/lib/types";

export const sampleWorlds: MoodWorld[] = [
  { id: "suspense", title: "Suspense & Mystery", kicker: "Mystery & Thriller", subtitle: "Secrets", tint: "#1b4a6b", genres: ["Mystery"] },
  { id: "action", title: "Action & Adrenaline", kicker: "Action & Adrenaline", subtitle: "Pace", tint: "#a8382a", genres: ["Action"] },
];

export function sampleMovies(n: number): Movie[] {
  return Array.from({ length: n }, (_, i) => {
    const num = String(i + 1).padStart(2, "0");
    return {
      id: `demo-${num}`,
      title: `Demo-Film ${num}`,
      kind: "film" as const,
      year: 2020,
      runtime_min: 120,
      original_language: "en",
      genres: ["Action"],
      world_ids: [i % 2 ? "suspense" : "action"],
      top_tags: ["dark"],
      overview: "Placeholder",
      directors: ["Jane Doe"],
      cast_top: ["A. Actor"],
      movielens_id: null,
      imdb_id: `tt00000${num}`,
      wikidata_id: null,
      wikipedia_title: null,
      release_date_de: null,
      poster_url: `https://picsum.photos/seed/p${num}/300/450`,
      horizontal_poster_url: `https://picsum.photos/seed/h${num}/720/405`,
      backdrop_url: `https://picsum.photos/seed/b${num}/1280/720`,
      youtube_key: "placeholder",
      ml_rating: 3.8,
      ml_rating_count: 1000,
      availability: { in_cinema_de: true, streaming_de: null, subscription_services: [] },
      is_placeholder: true,
    };
  });
}

export function sampleRanked(n: number): RankedMovie[] {
  return sampleMovies(n).map((movie, i) => ({ movie, score: 0.9 - i * 0.01, match_percent: 90 - i, reasons: [] }));
}

const movies12 = sampleMovies(12);
const homeRows = {
  suspense: movies12.filter((m) => m.world_ids.includes("suspense")),
  action: movies12.filter((m) => m.world_ids.includes("action")),
};
export const sampleHome: HomeData = {
  worlds: sampleWorlds,
  rows: homeRows,
  // the first half of each world's films are its newest top-rated, the rest its classics
  newest: Object.fromEntries(Object.entries(homeRows).map(([w, ms]) => [w, ms.slice(0, Math.ceil(ms.length / 2)).map((m) => m.id)])),
  newest_from: 2019,
  newest_years: 8,
  classics_before: 2019,
  titles: ["Demo-Film 01", "Demo-Film 02", "Demo-Film 03"],
};

export function mockMatchMedia(matches: (query: string) => boolean) {
  window.matchMedia = ((query: string) => ({
    matches: matches(query),
    media: query,
    onchange: null,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
