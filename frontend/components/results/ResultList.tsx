"use client";

import { useEffect, useState } from "react";
import RelatedRow, { foundText, LoadingBar, type Sweep } from "@/components/genre/RelatedRow";
import BestMatches from "@/components/results/BestMatches";
import { search, type DiscoverResult, type Relaxation } from "@/lib/api";
import type { Criteria } from "@/lib/searchState";
import type { Movie, RankedMovie } from "@/lib/types";

// two rows: in front up to BEST_MAX films from BEST_PERCENT (at least the MIN_SHOWN best, so a weak search still shows
// something), large and with why they fit; below them the further films from MORE_PERCENT, MORE_MAX at a time in a
// running row (loaded from the API in pages of LIMIT). Fixed bars, not a gap to the best match: another tag lowers
// every score, and a gap would then let in more films
const LIMIT = 50;
const MIN_SHOWN = 3;
const BEST_MAX = 6;
const BEST_PERCENT = 70;
const MORE_FLOORS = [70, 60, 50]; // the row below starts at the highest of these that still holds about MORE_MAX films
const MORE_PERCENT = 50; // the lowest floor: with no film from it, the films that fit one of the moods (one_mood)
const MORE_MAX = 30; // films in the running row at a time; its « » arrows run quickly to the previous / next ones
const count = new Intl.NumberFormat("en-US");

type Props = {
  criteria: Criteria;
  onOpen: (m: Movie) => void;
  onMeta?: (meta: Omit<DiscoverResult, "items">) => void;
  onRelax?: (c: Criteria, label: string) => void; // a search that finds too little offers ways to widen it
  widened?: { from: Criteria; labels: string[] } | null; // the user widened the search: say so, mark what films miss
  tagNames?: Record<number, string>; // for the explanation: the moods by name
};

type OneMood = { tag: string; count: number }[];

/** "How these results came about": what was searched, what the match means, why the rows start where they do,
 *  and how a search no film fully meets was answered. */
export function explainLines(criteria: Criteria, names: Record<number, string>, floor: number, oneMood: OneMood | null): string[] {
  const moods = criteria.tags
    .filter((t) => t.mode !== "not")
    .map((t) => `${names[t.idx] ?? "a mood"} (${"★".repeat(Math.round(t.weight / 2))}${t.mode === "must" ? ", must" : ""})`);
  const not = criteria.tags.filter((t) => t.mode === "not").map((t) => names[t.idx] ?? "a mood");
  const also = [
    criteria.person ? `with ${criteria.person}` : null,
    criteria.title ? `titled “${criteria.title}”` : null,
    criteria.year_from || criteria.year_to ? `from ${criteria.year_from ?? "…"} to ${criteria.year_to ?? "…"}` : null,
    not.length ? `without ${not.join(", ")}` : null,
  ].filter(Boolean);
  const wish = [moods.length ? `your moods ${moods.join(" and ")}` : "your taste", ...also].join(", ");
  const out = [
    `Searched for ${wish}.`,
    "Match %: fit to this search, moods first (MovieLens Tag Genome), then plot, people, 👍/👎, rating and fame. Not a review score.",
    `Top: the 6 best from 70% (at least 3). Below: more from ${floor}% (70% with many strong films, else 60 or 50%).`,
  ];
  if (oneMood)
    out.push(
      `No film has all your moods (none reached 50%): these fit at least one (${oneMood
        .map((m) => `${m.tag}: ${m.count}`)
        .join(", ")}); ≠ marks what a film lacks.`,
    );
  return out;
}

/** The best matches as one endless row at the bottom, like the genre page; the header gives the real number and
 *  never claims completeness, and every card says why it matches. */
/** The floor of the row below: with many strong films from 70%, with a middling number from 60%, else from 50%,
 *  counted on the first page (the API ranks by match, so it holds the strongest). */
export function moreFloor(percents: number[]): number {
  return MORE_FLOORS.find((f) => percents.filter((p) => p >= f).length >= MORE_MAX) ?? MORE_PERCENT;
}

const fmt = new Intl.NumberFormat("en-US");

/** The count above the films: the good matches (from the row's floor), not every film the hard limits let through
 *  ("50 films found" for Tom Cruise read as fifty matches when none reached 50%); the whole number comes after. */
export function countText(good: number, more: boolean, floor: number, total: number, capped: boolean, closest: number): string {
  const all = `${fmt.format(total)}${capped ? "+" : ""} films searched`;
  if (good === 0) return `No film matches well · the ${closest} closest of ${all}`;
  if (good >= total && !more && !capped) return foundText(total);
  return `${fmt.format(good)}${more ? "+" : ""} good ${good === 1 ? "match" : "matches"} from ${floor}% · ${all}`;
}

export default function ResultList({ criteria, onOpen, onMeta, onRelax, widened, tagNames = {} }: Props) {
  const [explain, setExplain] = useState(false);
  const [oneMood, setOneMood] = useState<{ key: string; parts: OneMood | null }>({ key: "", parts: null });
  const [items, setItems] = useState<RankedMovie[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [capped, setCapped] = useState(false);
  const [extended, setExtended] = useState(false);
  // the options belong to the search they were computed for; while the next one loads they are stale
  const [relaxFor, setRelaxFor] = useState<{ key: string; options: Relaxation[] }>({ key: "", options: [] });
  const [error, setError] = useState(false);
  const [shownKey, setShownKey] = useState<string | null>(null); // the search the shown results belong to
  // further pages of 50 (» / «), kept with the search they belong to so a new search starts on page one again
  const [more, setMore] = useState<{ key: string; pages: RankedMovie[][] }>({ key: "", pages: [] });
  const [page, setPage] = useState<{ key: string; n: number }>({ key: "", n: 0 });
  const [loadingMore, setLoadingMore] = useState(false);
  // » / « run quickly through the row to the other page before it is swapped in (the page it goes to)
  const [sweepTo, setSweepTo] = useState<{ key: string; n: number } | null>(null);
  const key = JSON.stringify(criteria);
  const fromKey = widened ? JSON.stringify(widened.from) : "";

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      const from = fromKey ? (JSON.parse(fromKey) as Criteria) : undefined;
      const r = await search(JSON.parse(key) as Criteria, 0, LIMIT, from);
      if (cancelled) return;
      if (!r.ok) {
        setShownKey(key);
        return setError(true);
      }
      setError(false);
      setShownKey(key);
      setItems(r.data.items);
      setTotal(r.data.total);
      setCapped(Boolean(r.data.total_capped));
      setExtended(r.data.extended_used);
      setRelaxFor({ key, options: r.data.relaxations ?? [] });
      setOneMood({ key, parts: r.data.one_mood ?? null });
      onMeta?.({
        total: r.data.total,
        hidden_by_exclusion: r.data.hidden_by_exclusion,
        extended_used: r.data.extended_used,
        corrected_person: r.data.corrected_person,
        corrected_title: r.data.corrected_title,
        hidden_by: r.data.hidden_by,
      });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [key, fromKey, onMeta]);

  const loading = shownKey !== key;
  if (error && !loading) return <p className="results-error">Couldn&apos;t load films</p>;
  if (total === null) return <LoadingBar />;
  const relaxations = relaxFor.key === key ? relaxFor.options : [];
  const widen =
    onRelax && relaxations.length > 0 ? (
      <div className="results-relax-bar">
        <span>{items.length ? `Only ${count.format(total)} films match every wish. More with:` : "Nothing matches every wish. Try:"}</span>
        {relaxations.map((o) => (
          <button key={o.id} type="button" className="results-relax" onClick={() => onRelax(o.criteria, o.label)}>
            {o.label} · {count.format(o.count)} films
          </button>
        ))}
      </div>
    ) : null;
  const note = widened?.labels.length ? (
    <p className="results-widened">Widened: {widened.labels.join("; ")} — films marked ≠ miss part of your wish</p>
  ) : null;
  // a person or title the widening never drops (it is the wish itself): if nothing is found, say which and
  // offer the search without it (a misspelt name is already matched fuzzily by the backend)
  const identity = criteria.person
    ? { text: `👤 ${criteria.person}`, what: "person", without: { ...criteria, person: null }, label: `without ${criteria.person}` }
    : criteria.title
      ? { text: `🔤 “${criteria.title}”`, what: "title", without: { ...criteria, title: null }, label: `without “${criteria.title}”` }
      : null;
  if (items.length === 0)
    return (
      <>
        {loading && <LoadingBar />}
        {identity && relaxFor.key === key ? (
          <div className="results-relax-bar">
            <span>Nothing found with {identity.text}</span>
            {onRelax && (
              <button type="button" className="results-relax" onClick={() => onRelax(identity.without, identity.label)}>
                Search without this {identity.what}
              </button>
            )}
          </div>
        ) : (
          <p className="results-head">No matches in the CineSense catalogue</p>
        )}
        {note}
        {widen}
      </>
    );
  const all = [items, ...(more.key === key ? more.pages : [])].flat();
  const best = all.slice(0, BEST_MAX).filter((r, i) => i < MIN_SHOWN || r.match_percent >= BEST_PERCENT);
  const floor = moreFloor(items.map((r) => r.match_percent));
  const parts = oneMood.key === key ? oneMood.parts : null; // the films fit one mood each, none all of them
  const rest = all.slice(best.length).filter((r) => r.match_percent >= floor);
  const chunks = Math.max(1, Math.ceil(rest.length / MORE_MAX));
  const n = page.key === key ? Math.min(page.n, chunks - 1) : 0;
  const shownOf = (p: number) => rest.slice(p * MORE_MAX, (p + 1) * MORE_MAX);
  const shown = shownOf(n);
  // the API may hold more above the bar: the loaded films fill whole pages and the last still clears it
  const last = all[all.length - 1];
  const canLoad = all.length < total && all.length % LIMIT === 0 && last.match_percent >= floor;
  const canNext = !loading && ((n + 1) * MORE_MAX < rest.length || canLoad);
  const next = async () => {
    // the next page from what is loaded, unless they would be fewer and the API holds more: then load first
    if ((n + 2) * MORE_MAX <= rest.length || (!canLoad && (n + 1) * MORE_MAX < rest.length)) return setSweepTo({ key, n: n + 1 });
    setLoadingMore(true);
    const r = await search(criteria, all.length, LIMIT, widened?.from);
    setLoadingMore(false);
    if (!r.ok || r.data.items.length === 0) return;
    setMore({ key, pages: [...(more.key === key ? more.pages : []), r.data.items] });
    if (r.data.items.some((x) => x.match_percent >= floor)) setSweepTo({ key, n: n + 1 });
  };
  // during a sweep the row holds both pages; it ends where the other page alone starts, then that page is swapped in
  const to = sweepTo && sweepTo.key === key && sweepTo.n < chunks ? sweepTo.n : null;
  const target = to === null ? [] : shownOf(to);
  const rowItems = to === null ? shown : to > n ? [...shown, ...target] : [...target, ...shown];
  const sweep: Sweep | null =
    to === null
      ? null
      : {
          from: to > n ? 0 : target.length,
          to: to > n ? shown.length : 0,
          onDone: () => {
            setPage({ key, n: to });
            setSweepTo(null);
          },
        };
  const start = best.length + n * MORE_MAX; // films ranked before this row
  const available = `${best.length + rest.length}${canLoad ? "+" : ""}`; // every film above the bar loaded so far
  const streaming = criteria.availability === "stream";
  const bestLabel = (
    <>
      {parts ? `The ${best.length} best of them` : total > best.length ? `The ${best.length} best matches` : "All matches"}
      {streaming && (
        <span className="related-hint">
          {" "}
          · {best.filter((r) => r.movie.availability.streaming_de?.length).length} of these {best.length} confirmed on streaming
        </span>
      )}
      {extended && <span className="results-extended"> · includes titles just added from Wikidata</span>}
    </>
  );
  const moreLabel = (
    <>
      {`${shown.length} more matches from ${floor}%`}
      <span className="related-hint">
        {" "}
        · {start + 1}–{start + shown.length} of {available}
      </span>
    </>
  );
  return (
    <>
      {/* the notes about this search on the left, how its results came about on the right, side by side */}
      <div className="results-info">
        <div className="results-info__left">
          {note}
          {widen}
        </div>
        <button type="button" className="results-explain-btn" aria-expanded={explain} onClick={() => setExplain((v) => !v)}>
          ⓘ How these results came about
        </button>
        {explain && (
          <aside className="results-explain" aria-label="How these results came about">
            <ul>
              {explainLines(criteria, tagNames, floor, parts).map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </aside>
        )}
      </div>
      <div className="results-count-line">
        <p className="related-count results-count">
          {parts
            ? `${fmt.format(total)} ${total === 1 ? "film fits" : "films fit"} one of your moods · none has them all`
            : countText(best.filter((r) => r.match_percent >= floor).length + rest.length, canLoad, floor, total, capped, best.length)}
        </p>
      </div>
      {(loading || loadingMore) && <LoadingBar />}
      <BestMatches items={best} onSelect={onOpen} label={bestLabel} streamCheck={streaming} busy={loading} />
      {rowItems.length > 0 && (
        <div className="results-more-row">
          <RelatedRow
            key={n} // a new page starts at its first film
            items={rowItems}
            onSelect={onOpen}
            label={moreLabel}
            streamCheck={streaming}
            name="Results"
            showReasons
            busy={loading || loadingMore}
            bar={false}
            drift={false}
            bounded // a row with a start and an end the mouse slides through
            sweep={sweep}
            arrows
            paging={{
              size: MORE_MAX,
              prev: n > 0 && !loading ? () => setSweepTo({ key, n: n - 1 }) : null,
              next: canNext && !loadingMore ? next : null,
            }}
          />
        </div>
      )}
    </>
  );
}
