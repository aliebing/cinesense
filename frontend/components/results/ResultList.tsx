"use client";

import { useEffect, useState } from "react";
import RelatedRow, { foundText, LoadingBar, type Sweep } from "@/components/genre/RelatedRow";
import BestMatches from "@/components/results/BestMatches";
import { search, type DiscoverResult, type Relaxation } from "@/lib/api";
import type { Criteria } from "@/lib/searchState";
import type { Movie, RankedMovie } from "@/lib/types";

// two rows: in front up to BEST_MAX films from BEST_PERCENT (at least the MIN_SHOWN best, so a weak search still shows
// something), large and with why they fit; below them every further film from MORE_PERCENT, as a running row paged by
// 50. Fixed bars, not a gap to the best match: another tag lowers every score, and a gap would then let in more films
const LIMIT = 50;
const MIN_SHOWN = 3;
const BEST_MAX = 8;
const BEST_PERCENT = 70;
const MORE_PERCENT = 60;
const count = new Intl.NumberFormat("en-US");

type Props = {
  criteria: Criteria;
  onOpen: (m: Movie) => void;
  onMeta?: (meta: Omit<DiscoverResult, "items">) => void;
  onRelax?: (c: Criteria, label: string) => void; // a search that finds too little offers ways to widen it
  widened?: { from: Criteria; labels: string[] } | null; // the user widened the search: say so, mark what films miss
};

/** The best matches as one endless row at the bottom, like the genre page; the header gives the real number and
 *  never claims completeness, and every card says why it matches. */
export default function ResultList({ criteria, onOpen, onMeta, onRelax, widened }: Props) {
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
  const pages = [items, ...(more.key === key ? more.pages : [])];
  const n = page.key === key ? Math.min(page.n, pages.length - 1) : 0;
  const current = pages[n];
  const first = n * LIMIT; // films before this page
  const best = pages[0].slice(0, BEST_MAX).filter((r, i) => i < MIN_SHOWN || r.match_percent >= BEST_PERCENT);
  const shownOf = (p: number) => (p === 0 ? pages[0].slice(best.length) : pages[p]).filter((r) => r.match_percent >= MORE_PERCENT);
  const shown = shownOf(n);
  // a next page only while this one still ends above the bar: then the next may hold more that do
  const last = current[current.length - 1];
  const canNext = !loading && current.length === LIMIT && last.match_percent >= MORE_PERCENT && first + LIMIT < total;
  const next = async () => {
    if (n + 1 < pages.length) return setSweepTo({ key, n: n + 1 });
    setLoadingMore(true);
    const r = await search(criteria, first + LIMIT, LIMIT, widened?.from);
    setLoadingMore(false);
    if (!r.ok || r.data.items.length === 0) return;
    setMore({ key, pages: [...pages.slice(1), r.data.items] });
    setSweepTo({ key, n: n + 1 });
  };
  // during a sweep the row holds both pages; it ends where the other page alone starts, then that page is swapped in
  const to = sweepTo && sweepTo.key === key && sweepTo.n < pages.length ? sweepTo.n : null;
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
  const moreLabel = (
    <>
      {n > 0 ? `Matches ${first + 1}–${first + shown.length}` : `${shown.length} more matches from ${MORE_PERCENT}%`}
      {n > 0 && !loading && !sweep && (
        <button type="button" className="results-page-btn" onClick={() => setSweepTo({ key, n: n - 1 })} aria-label={`Previous ${LIMIT}`} title={`Previous ${LIMIT}`}>
          ‹ Previous {LIMIT}
        </button>
      )}
      {canNext && !sweep && (
        <button type="button" className="results-page-btn" onClick={next} disabled={loadingMore} aria-label={`Next ${LIMIT}`} title={`Next ${LIMIT}`}>
          Next {LIMIT} ›
        </button>
      )}
    </>
  );
  return (
    <>
      {note}
      {widen}
      <p className="related-count results-count">{foundText(total, capped)}</p>
      {(loading || loadingMore) && <LoadingBar />}
      {n === 0 && <BestMatches items={best} onSelect={onOpen} label={bestLabel} streamCheck={streaming} busy={loading} />}
      {(rowItems.length > 0 || n > 0) && (
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
            loop // an endless row the mouse slides left or right, even when its films would fit
            sweep={sweep}
            arrows
          />
        </div>
      )}
    </>
  );
}
