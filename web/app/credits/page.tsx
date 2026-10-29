import Link from "next/link";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";

const SOURCES = [
  {
    name: "MovieLens (GroupLens Research)",
    what: "Ratings, genres and the Tag Genome mood tags for about 16,000 films.",
    licence: "Research and education use with acknowledgement; the dataset is not redistributed.",
    cite: "F. Maxwell Harper and Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context. ACM TiiS 5(4).",
    href: "https://grouplens.org/datasets/movielens/",
  },
  {
    name: "Wikidata",
    what: "Film identifiers, cast and directors, runtime, language, German release dates and YouTube trailer ids.",
    licence: "CC0 1.0 (public domain).",
    href: "https://www.wikidata.org/",
  },
  {
    name: "Wikipedia",
    what: "Plot summaries used for search and explanations; each film links to its article.",
    licence: "CC BY-SA 4.0.",
    href: "https://en.wikipedia.org/",
  },
  {
    name: "Streaming Availability API by Movie of the Night",
    what: "Where films stream in Germany, plus posters and backdrops.",
    licence: "Used under the API terms with attribution.",
    href: "https://www.movieofthenight.com/about/api",
  },
  {
    name: "YouTube",
    what: "Trailers are shown in the embedded YouTube player; missing trailer ids may be looked up via the YouTube Data API.",
    licence: "YouTube API Services Terms.",
    href: "https://www.youtube.com/t/terms",
  },
  {
    name: "Unsplash",
    what: "Curtain photo by Ambitious Studio* | Rick Barrett.",
    licence: "Unsplash License.",
    href: "https://unsplash.com/photos/a-red-curtain-with-a-black-background-AwsdyjRm-kw",
  },
];

export default function CreditsPage() {
  return (
    <CinemaFrame>
      <FogLight tint="#1b4a6b" reduced />
      <div className="results-page credits">
        <header className="genre-top results-top">
          <Link href="/">CineSense &nbsp;← Back to home</Link>
        </header>
        <h1>Credits &amp; data sources</h1>
        <p>
          CineSense is a non-commercial student project. It does not use TMDB, whose terms do not allow use in AI
          applications. No film facts are invented: everything shown comes from the sources below.
        </p>
        <ul className="credits-list">
          {SOURCES.map((s) => (
            <li key={s.name}>
              <h2>
                <a href={s.href} target="_blank" rel="noreferrer">
                  {s.name}
                </a>
              </h2>
              <p>{s.what}</p>
              <p className="credits-licence">{s.licence}</p>
              {s.cite && <p className="credits-licence">{s.cite}</p>}
            </li>
          ))}
        </ul>
        <section className="credits-privacy">
          <h2>Privacy</h2>
          <p>
            CineSense uses YouTube API Services. By watching trailers you agree to the{" "}
            <a href="https://www.youtube.com/t/terms" target="_blank" rel="noreferrer">
              YouTube Terms of Service
            </a>
            ; Google&apos;s handling of data is described in the{" "}
            <a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer">
              Google Privacy Policy
            </a>
            . Trailers use the privacy-enhanced youtube-nocookie.com player. CineSense stores no personal data; your search
            state stays in this browser tab.
          </p>
        </section>
      </div>
    </CinemaFrame>
  );
}
