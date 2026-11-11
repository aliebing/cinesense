"use client";

import { useEffect, useRef, useState } from "react";
import RelatedRow, { foundText, LoadingBar, type Sweep } from "@/components/genre/RelatedRow";
import BestMatches from "@/components/results/BestMatches";
import { search, type DiscoverResult, type Relaxation } from "@/lib/api";
import type { Criteria } from "@/lib/searchState";
import type { Movie, RankedMovie } from "@/lib/types";

// in front up to BEST_MAX films from BEST_PERCENT (at least the MIN_SHOWN best, so a weak search still shows
// something), large and with why they fit; below them one row the mouse slides through with every further film from
// the floor (chooseFloor), MORE_MAX at a time; its « » run quickly to the previous / next MORE_MAX. Every film from the
// floor is loaded from the API in pages of LIMIT in the background. Fixed bars, not a gap to the best match: another
// tag lowers every score, and a gap would then let in more films
const LIMIT = 50;
const MIN_SHOWN = 3;
const BEST_MAX = 6;
const BEST_PERCENT = 70;
const FLOOR = 60; // the grid shows every film from 60% ...
const HIGH_FLOORS = [70, 80, 90]; // ... unless more than SHOW_MAX reach it: then from the lowest of these that fit
const LOW_FLOOR = 50; // ... and from 50% when fewer than FEW films reach 60%
const SHOW_MAX = 500;
const FEW = 28;
const MORE_FLOORS = [70, 60, 50]; // without counts from the API (older server): judged on the first page
const MORE_MAX = 30;
const WEAK_FLOOR = 20; // fewer than FEW good films: the grid goes on with weaker ones down to this
const WEAK_MAX = 29; // ... but only one page of them

type Props = {
  criteria: Criteria;
  onOpen: (m: Movie) => void;
  onMeta?: (meta: Omit<DiscoverResult, "items">) => void;
  onRelax?: (c: Criteria, label: string) => void; // a search that finds too little offers ways to widen it
  widened?: { from: Criteria; labels: string[] } | null; // the user widened the search: say so, mark what films miss
  tagNames?: Record<number, string>; // for the explanation: the moods by name
};

/** "How these results came about": what was searched, what the match means, why the rows start where they do,
 *  and how a search no film fully meets was answered. */
export function explainLines(
  criteria: Criteria,
  names: Record<number, string>,
  floor: number,
  widenedBy: string | null = null,
  weak = false,
): string[] {
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
    `Top: the 6 best from 70% (at least 3). Below: every further film from ${floor}% (from 60%; higher when more than 500 films reach 60%, from 50% when fewer than 28 do).`,
  ];
  if (weak) out.push(`Few films fit well, so the films below go on with weaker ones of this search (below ${floor}%, down to ${WEAK_FLOOR}%).`);
  if (widenedBy)
    out.push(`Too few films match every wish, so the films below come from the search with “${widenedBy}”, the change that alters your wish least; your search itself stays as it is.`);
  return out;
}

/** The best matches as one endless row at the bottom, like the genre page; the header gives the real number and
 *  never claims completeness, and every card says why it matches. */
/** The widening shown when too few films match every wish: the least intrusive one that finds enough films
 *  (the options come least intrusive first), else the one that finds the most (as the agent picks). */
export function pickWidening(options: Relaxation[]): Relaxation | null {
  return options.find((o) => o.count >= MIN_SHOWN) ?? [...options].sort((a, b) => b.count - a.count)[0] ?? null;
}

/** The films a first page of results shows, in order: the best in front, then the films below (from the floor, or
 *  with few strong films the weaker ones down to WEAK_FLOOR, at most WEAK_MAX). The genre page's search uses it. */
export function selectRow(items: RankedMovie[], counts?: Record<string, number>, capped = false): RankedMovie[] {
  const best = items.slice(0, BEST_MAX).filter((r, i) => i < MIN_SHOWN || r.match_percent >= BEST_PERCENT);
  const floor = chooseFloor(counts, capped, items.map((r) => r.match_percent));
  const strong = items.slice(best.length).filter((r) => r.match_percent >= floor);
  const filled = strong.length < MORE_MAX ? items.slice(best.length).filter((r) => r.match_percent >= WEAK_FLOOR) : strong;
  const weak = filled.length > strong.length;
  return [...best, ...(weak ? filled.slice(0, Math.max(strong.length, WEAK_MAX)) : filled)];
}

/** The floor of the row below without counts from the API: with many strong films from 70%, with a middling number
 *  from 60%, else from 50%, counted on the first page (the API ranks by match, so it holds the strongest). */
export function moreFloor(percents: number[]): number {
  return MORE_FLOORS.find((f) => percents.filter((p) => p >= f).length >= MORE_MAX) ?? LOW_FLOOR;
}

/** The floor of the grid, from the API's counts over the whole search: every film from 60%; when more than 500 reach
 *  60%, the lowest of 70/80/90% that keeps it to 500; when fewer than 28 reach 60%, from 50%. A capped mood search
 *  (it kept only its best 500) counts 500 as more. */
export function chooseFloor(counts: Record<string, number> | undefined, capped: boolean, percents: number[]): number {
  const at = (f: number) => counts?.[String(f)];
  if (at(FLOOR) === undefined) return moreFloor(percents);
  const over = (f: number) => (at(f) ?? 0) > SHOW_MAX || (capped && (at(f) ?? 0) >= SHOW_MAX);
  if (over(FLOOR)) return HIGH_FLOORS.find((f) => !over(f)) ?? HIGH_FLOORS[HIGH_FLOORS.length - 1];
  return (at(FLOOR) ?? 0) < FEW ? LOW_FLOOR : FLOOR;
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

/** Loads the next page as soon as it is mounted: the row holds every film from the floor (at most SHOW_MAX), and
 *  further pages cost no Streaming API lookups. Mounted again after each page while more are due. */
function LoadNext({ onLoad }: { onLoad: () => void }) {
  const cb = useRef(onLoad);
  useEffect(() => {
    cb.current = onLoad;
  });
  useEffect(() => {
    cb.current();
  }, []);
  return null;
}

export default function ResultList({ criteria, onOpen, onMeta, onRelax, widened, tagNames = {} }: Props) {
  const [explain, setExplain] = useState(false);
  const [items, setItems] = useState<RankedMovie[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [capped, setCapped] = useState(false);
  const [counts, setCounts] = useState<Record<string, number> | undefined>(undefined);
  const [extended, setExtended] = useState(false);
  // the options belong to the search they were computed for; while the next one loads they are stale
  const [relaxFor, setRelaxFor] = useState<{ key: string; options: Relaxation[] }>({ key: "", options: [] });
  // too few films match every wish: the films of the widening that changes the wish least, shown below as
  // information (the search itself stays as the user set it, so there is nothing to undo)
  const [alt, setAlt] = useState<{ key: string; label: string; items: RankedMovie[] } | null>(null);
  const [error, setError] = useState(false);
  const [shownKey, setShownKey] = useState<string | null>(null); // the search the shown results belong to
  // further pages of 50, kept with the search they belong to so a new search starts on page one again
  const [more, setMore] = useState<{ key: string; pages: RankedMovie[][] }>({ key: "", pages: [] });
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState<{ key: string; n: number }>({ key: "", n: 0 }); // the MORE_MAX shown in the row
  const [sweepTo, setSweepTo] = useState<{ key: string; n: number } | null>(null); // the row runs to that page
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
      setCounts(r.data.match_counts);
      setExtended(r.data.extended_used);
      setRelaxFor({ key, options: r.data.relaxations ?? [] });
      const option = pickWidening(r.data.relaxations ?? []);
      if (option) {
        const w = await search(option.criteria, 0, LIMIT, JSON.parse(key) as Criteria); // ≠ marks what each film misses
        if (cancelled) return;
        const exact = new Set(r.data.items.map((x) => x.movie.id));
        setAlt(w.ok ? { key, label: option.label, items: w.data.items.filter((x) => !exact.has(x.movie.id)) } : null);
      } else setAlt(null);
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
  const widenedRow = alt && alt.key === key && alt.items.length > 0 ? alt : null;
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
  if (items.length === 0 && !widenedRow)
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
      </>
    );
  const all = [items, ...(more.key === key ? more.pages : [])].flat();
  const best = all.slice(0, BEST_MAX).filter((r, i) => i < MIN_SHOWN || r.match_percent >= BEST_PERCENT);
  const floor = chooseFloor(counts, capped, items.map((r) => r.match_percent));
  // every film from the floor the whole search holds (the API counts them), at most SHOW_MAX
  const good = counts?.[String(floor)];
  const strong = all.slice(best.length).filter((r) => r.match_percent >= floor);
  // few good films: the grid goes on with the weaker ones (down to WEAK_FLOOR), saying so
  // ("Tom Cruise + space travel" has one strong film and many more with Tom Cruise)
  const fewGood = good !== undefined ? good < FEW : strong.length < MORE_MAX;
  const filled = fewGood ? all.slice(best.length).filter((r) => r.match_percent >= WEAK_FLOOR) : strong;
  const weak = !widenedRow && filled.length > strong.length;
  const rest = widenedRow ? widenedRow.items : weak ? filled.slice(0, Math.max(strong.length, WEAK_MAX)) : strong.slice(0, SHOW_MAX - best.length);
  // the API may hold more above the floor: the loaded films fill whole pages and the last still clears it
  const last = all[all.length - 1];
  const bestGood = best.filter((r) => r.match_percent >= floor).length;
  const target = good !== undefined ? Math.min(good, SHOW_MAX) - bestGood : null; // films the grid will hold
  const canLoad =
    !widenedRow && !weak && all.length < total && all.length % LIMIT === 0 && last.match_percent >= floor &&
    best.length + rest.length < SHOW_MAX && (target === null || rest.length < target);
  const loadMore = async () => {
    if (loadingMore || !canLoad) return;
    setLoadingMore(true);
    const r = await search(criteria, all.length, LIMIT, widened?.from, false); // no image or trailer lookups
    setLoadingMore(false);
    if (!r.ok || r.data.items.length === 0) return;
    setMore({ key, pages: [...(more.key === key ? more.pages : []), r.data.items] });
  };
  // the row shows MORE_MAX films at a time; « » run to the previous / next ones (loaded in the background)
  const chunks = Math.max(1, Math.ceil(rest.length / MORE_MAX));
  const n = page.key === key ? Math.min(page.n, chunks - 1) : 0;
  const shownOf = (p: number) => rest.slice(p * MORE_MAX, (p + 1) * MORE_MAX);
  const shown = shownOf(n);
  // during a sweep the row holds both pages; it ends where the other page alone starts, then that page is swapped in
  const to = sweepTo && sweepTo.key === key && sweepTo.n < chunks ? sweepTo.n : null;
  const toItems = to === null ? [] : shownOf(to);
  const rowItems = to === null ? shown : to > n ? [...shown, ...toItems] : [...toItems, ...shown];
  const sweep: Sweep | null =
    to === null
      ? null
      : {
          from: to > n ? 0 : toItems.length,
          to: to > n ? shown.length : 0,
          onDone: () => {
            setPage({ key, n: to });
            setSweepTo(null);
          },
        };
  const streaming = criteria.availability === "stream";
  const bestLabel = (
    <>
      {total > best.length ? `The ${best.length} best matches` : "All matches"}
      {streaming && (
        <span className="related-hint">
          {" "}
          · {best.filter((r) => r.movie.availability.streaming_de?.length).length} of these {best.length} confirmed on streaming
        </span>
      )}
      {extended && <span className="results-extended"> · includes titles just added from Wikidata</span>}
    </>
  );
  const fmtN = (n: number) => fmt.format(n);
  const moreText = widenedRow
    ? `${items.length ? `Only ${total} ${total === 1 ? "film matches" : "films match"}` : "No film matches"} every wish · ${rest.length} more with: ${widenedRow.label}`
    : weak
      ? strong.length
        ? `${rest.length} more matches · ${strong.length} from ${floor}%, then weaker ones`
        : `${rest.length} weaker matches (below ${floor}%)`
      : `${fmtN(target ?? rest.length)}${target === null && canLoad ? "+" : ""} more matches from ${floor}%`;
  const moreLabel = (
    <>
      {moreText}
      {chunks > 1 && (
        <span className="related-hint">
          {" "}
          · {fmtN(n * MORE_MAX + 1)}–{fmtN(n * MORE_MAX + shown.length)}
        </span>
      )}
    </>
  );
  return (
    <>
      {/* the notes about this search on the left, how its results came about on the right, side by side */}
      <div className="results-info">
        <div className="results-info__left">
          {note}
        </div>
        <button type="button" className="results-explain-btn" aria-expanded={explain} onClick={() => setExplain((v) => !v)}>
          ⓘ How these results came about
        </button>
        {explain && (
          <aside className="results-explain" aria-label="How these results came about">
            <ul>
              {explainLines(criteria, tagNames, floor, widenedRow?.label ?? null, weak).map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </aside>
        )}
      </div>
      <div className="results-count-line">
        <p className="related-count results-count">
          {items.length === 0
            ? "No film matches every wish"
            : countText(
                good !== undefined && !widenedRow ? Math.min(good, SHOW_MAX) : bestGood + (widenedRow ? rest.length : strong.length),
                good === undefined && canLoad,
                floor,
                total,
                capped,
                best.length,
              )}
        </p>
      </div>
      {loading && <LoadingBar />}
      {best.length > 0 && <BestMatches items={best} onSelect={onOpen} label={bestLabel} streamCheck={streaming} busy={loading} />}
      {rest.length > 0 && (
        <div className="results-more-row">
          <RelatedRow
            key={n} // a new page starts at its first film
            items={rowItems}
            onSelect={onOpen}
            label={moreLabel}
            streamCheck={streaming}
            name="More matches"
            showReasons
            busy={loading}
            bar={false}
            drift={false}
            bounded // a row with a start and an end the mouse slides through
            sweep={sweep}
            arrows
            paging={{
              size: MORE_MAX,
              prev: n > 0 && !loading ? () => setSweepTo({ key, n: n - 1 }) : null,
              next: (n + 1) * MORE_MAX < rest.length && !loading ? () => setSweepTo({ key, n: n + 1 }) : null,
            }}
          />
          {canLoad && !loadingMore && <LoadNext onLoad={loadMore} />}
        </div>
      )}
    </>
  );
}
