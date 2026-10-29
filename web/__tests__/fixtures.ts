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
      year: 2020,
      runtime_min: 120,
      original_language: "en",
      genres: ["Action"],
      world_ids: [i % 2 ? "suspense" : "action"],
      overview: "Placeholder",
      poster_url: `https://picsum.photos/seed/p${num}/300/450`,
      backdrop_url: `https://picsum.photos/seed/b${num}/1280/720`,
      youtube_key: "placeholder",
      vote_average: 7.5,
      vote_count: 1000,
      age_rating_de: "12",
      availability: { in_cinema_de: true, streaming_flatrate_de: [] },
      is_placeholder: true,
    };
  });
}

export function sampleRanked(n: number): RankedMovie[] {
  return sampleMovies(n).map((movie, i) => ({ movie, score: 8 - i * 0.1, match_percent: 90 - i }));
}

export const sampleHome: HomeData = {
  worlds: sampleWorlds,
  tiles: sampleMovies(12),
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
