"use client";

import { stageWhyText } from "@/lib/why";
import { notFound, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import RelatedRow, { type Sweep } from "@/components/genre/RelatedRow";
import { pickWidening, selectRow } from "@/components/results/ResultList";
import StagePanel from "@/components/genre/StagePanel";
import Breadcrumb, { type Crumb } from "@/components/nav/Breadcrumb";
import MoodSummary from "@/components/search/MoodSummary";
import {
  discover,
  fitMovie,
  getMovie,
  getProfile,
  getRelated,
  getTags,
  getWorldMovies,
  getWorlds,
  type MoodFit,
  type ProfileSummary,
  search,
  sendFeedback,
  type Tag,
} from "@/lib/api";
import { type Criteria, hasAnyCriteria, steer, useSearchState } from "@/lib/searchState";
import type { MoodWorld, Movie, RankedMovie } from "@/lib/types";
import { useReducedMotion } from "@/lib/useReducedMotion";

type State =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "not_found" }
  | { kind: "ready"; world: MoodWorld; movie: Movie };

type Props = {
  worldId: string;
  filmId: string | null;
  /** opened with "Show results": the row holds the other matches of the whole search, with their reasons */
  fromSearch?: boolean;
};

export default function GenreView({ worldId, filmId, fromSearch = false }: Props) {
  const router = useRouter();
  const reduced = useReducedMotion();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [related, setRelated] = useState<RankedMovie[]>([]);
  // how many films the search behind the row found; null while the row holds the stage film's neighbours
  const [found, setFound] = useState<{ total: number; capped?: boolean } | null>(null);
  // the shared search state, shown read-only here (edited on the start and results pages): it ranks the row,
  // and ⚡ / 😂 add to it
  const [criteria, setCriteria] = useSearchState();
  const [tags, setTags] = useState<Tag[]>([]);
  const [hidden, setHidden] = useState(0);
  const [rowFromSearch, setRowFromSearch] = useState(fromSearch);
  // too few films for every wish: those that match (their ids) and the widening whose films follow them
  const [widenedRow, setWidenedRow] = useState<{ label: string; exact: Set<string> } | null>(null);
  // the row in pages of PAGE (« »), kept with the search it belongs to; a new search starts on page one
  const [page, setPage] = useState<{ key: string; n: number }>({ key: "", n: 0 });
  // « » run quickly through the row to the other page, which is loaded first (both are in the row meanwhile)
  const [pending, setPending] = useState<{ n: number; raw: RankedMovie[] } | null>(null);
  const loadedFor = useRef(""); // the row already holds this page (a finished « » run must not load it again)
  const criteriaKey = JSON.stringify(criteria);

  const [profile, setProfile] = useState<ProfileSummary | null>(null);
  const [feedbackVersion, setFeedbackVersion] = useState(0);
  const feedbackPending = useRef(false);
  const [stageReasons, setStageReasons] = useState<{ id: string; reasons: string[] } | null>(null);
  // opened from the homepage and a film picked in the row: the film it was picked as being like
  const [likeOf, setLikeOf] = useState<{ id: string; of: Movie } | null>(null);
  // how the stage film carries the wished moods, for a film the search did not rank (opened from a world)
  const [stageFit, setStageFit] = useState<{ id: string; key: string; fit: MoodFit[] } | null>(null);

  useEffect(() => {
    getTags().then((r) => r.ok && setTags(r.data));
    getProfile().then((r) => r.ok && setProfile(r.data));
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [worlds, ranked] = await Promise.all([getWorlds(), getWorldMovies(worldId)]);
      if (cancelled) return;
      if (!ranked.ok && ranked.error === "not_found") return setState({ kind: "not_found" });
      if (!worlds.ok || !ranked.ok) return setState({ kind: "error" });
      const world = worlds.data.find((w) => w.id === worldId);
      if (!world) return setState({ kind: "not_found" });
      let movie: Movie | undefined = ranked.data[0]?.movie;
      if (filmId) {
        const found = await getMovie(filmId);
        if (cancelled) return;
        if (!found.ok) return setState({ kind: found.error === "not_found" ? "not_found" : "error" });
        movie = found.data;
      }
      if (!movie) return setState({ kind: "not_found" });
      setState({ kind: "ready", world, movie });
    })();
    return () => {
      cancelled = true;
    };
  }, [worldId, filmId]);

  const stageId = state.kind === "ready" ? state.movie.id : null;
  useEffect(() => {
    const active = JSON.parse(criteriaKey);
    if (!stageId || !fromSearch || !active.tags?.length) return;
    let cancelled = false;
    fitMovie(stageId, active).then((r) => {
      if (!cancelled && r.ok) setStageFit({ id: stageId, key: criteriaKey, fit: r.data });
    });
    return () => {
      cancelled = true;
    };
  }, [stageId, criteriaKey, fromSearch]);
  const n = page.key === criteriaKey ? page.n : 0;
  // one page of the row: the search's matches (opened from the search) or the world's films ranked by the chips
  // (or by rating without any); one film more than a page, as the stage film may be among them
  const fetchPage = useCallback(
    async (active: Criteria, pageNo: number) => {
      const useSearch = fromSearch && hasAnyCriteria(active);
      // from the search: its first 50 films at once, chosen as the search page shows them (paged here by 30)
      const r = useSearch
        ? await search(active, 0, 50)
        : await discover({ ...active, world_id: worldId }, pageNo * PAGE, PAGE + 1);
      if (!r.ok) return null;
      const chosen = useSearch ? selectRow(r.data.items) : r.data.items;
      const base = {
        items: chosen,
        total: useSearch ? chosen.length : r.data.total,
        capped: useSearch ? false : Boolean(r.data.total_capped),
        hidden: r.data.hidden_by_exclusion,
        useSearch,
      };
      // like the search page: too few films for every wish, so the films of the widening that changes it least
      // follow them (one page; the search itself stays)
      const option = useSearch ? pickWidening(r.data.relaxations ?? []) : null;
      if (!option) return { ...base, widened: null };
      const w = await search(option.criteria, 0, 50, active);
      if (!w.ok) return { ...base, widened: null };
      const exact = new Set(r.data.items.map((x) => x.movie.id));
      const items = [...r.data.items, ...w.data.items.filter((x) => !exact.has(x.movie.id))];
      return { ...base, items, total: items.length, widened: { label: option.label, exact: r.data.items } };
    },
    [fromSearch, worldId],
  );
  const loadKey = `${criteriaKey}|${n}|${stageId}|${feedbackVersion}`;
  useEffect(() => {
    if (!stageId || loadedFor.current === loadKey) return;
    let cancelled = false;
    const active = JSON.parse(criteriaKey) as Criteria;
    // the stage film's own neighbours: the fallback when a search leaves nothing else to show
    // (a title search finds just the film on stage, and the row would stay empty)
    const loadRelated = () =>
      getRelated(stageId, worldId, LIKE_THIS).then((r) => {
        if (cancelled) return;
        setRelated(r.ok ? r.data : []);
        setFound(null);
        setWidenedRow(null);
        setRowFromSearch(false);
        setHidden(0);
        loadedFor.current = loadKey;
      });
    const t = setTimeout(async () => {
      // opened from the homepage: films like the one on stage, in its genre (the search plays no part here)
      if (!fromSearch) return loadRelated();
      const p = await fetchPage(active, n);
      if (cancelled) return;
      if (!p || (n === 0 && !p.items.some((x) => x.movie.id !== stageId))) return loadRelated();
      const onStage = p.items.find((x) => x.movie.id === stageId);
      if (onStage && p.useSearch) setStageReasons((s) => s ?? { id: onStage.movie.id, reasons: onStage.reasons });
      setRelated(p.items);
      setFound({ total: p.total, capped: p.capped });
      setWidenedRow(p.widened ? { label: p.widened.label, exact: new Set(p.widened.exact.map((x) => x.movie.id)) } : null);
      setRowFromSearch(p.useSearch);
      setHidden(p.hidden);
      loadedFor.current = loadKey;
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [stageId, worldId, criteriaKey, n, loadKey, fetchPage, fromSearch]);
  const turn = async (to: number) => {
    if (pending) return;
    if (rowFromSearch && found) return setPending({ n: to, raw: related }); // all loaded: just another page of it
    const p = await fetchPage(JSON.parse(criteriaKey) as Criteria, to);
    if (p && p.items.some((x) => x.movie.id !== stageId)) setPending({ n: to, raw: p.items });
  };

  if (state.kind === "not_found") {
    notFound();
    return null;
  }

  const select = (m: Movie) => {
    if (state.kind !== "ready") return;
    setStageReasons({ id: m.id, reasons: related.find((r) => r.movie.id === m.id)?.reasons ?? [] });
    if (!fromSearch) setLikeOf({ id: m.id, of: state.movie });
    setState({ ...state, movie: m });
    router.replace(`/world/${worldId}?film=${m.id}${fromSearch ? "&from=search" : ""}`, { scroll: false });
  };

  const feedbackFor = (id: string) =>
    profile?.liked.some((f) => f.id === id) ? 1 : profile?.disliked.some((f) => f.id === id) ? -1 : 0;

  const giveFeedback = async (value: -1 | 0 | 1) => {
    if (state.kind !== "ready" || feedbackPending.current) return; // a double click counts once
    feedbackPending.current = true;
    const r = await sendFeedback(state.movie.id, value).finally(() => {
      feedbackPending.current = false;
    });
    if (!r.ok) return;
    setProfile(r.data);
    setFeedbackVersion((v) => v + 1); // the row re-ranks with the new profile
  };

  const steerSession = (kind: "action" | "funny") => {
    const idx = tags.find((t) => t.tag === kind)?.idx;
    if (idx !== undefined) setCriteria(steer(criteria, idx));
  };

  const stageWhy = (m: Movie, w: MoodWorld) => {
    if (!fromSearch) return likeWhy(m, w.title, likeOf?.id === m.id ? likeOf.of : null);
    const reasons = stageReasons?.id === m.id ? stageReasons.reasons : [];
    const fit = stageFit?.id === m.id && stageFit.key === criteriaKey ? stageFit.fit : null;
    return stageWhyText(m, w.title, reasons, fit);
  };

  const world = state.kind === "ready" ? state.world : null;
  const movie = state.kind === "ready" ? state.movie : null;
  // one page of the row; a widened row is shown whole (it is loaded as one)
  // one page of the row: from the search every film is loaded, a page is a slice of it; otherwise each page is fetched
  const allLoaded = rowFromSearch && found !== null;
  const others_ = (raw: RankedMovie[]) => (movie ? raw.filter((r) => r.movie.id !== movie.id) : []);
  // a few films over a page stay on it (the search page's 3 + 29 less the stage film): no page for a single film
  const size = allLoaded && others_(related).length <= PAGE + 5 ? Number.MAX_SAFE_INTEGER : PAGE;
  const pageOf = (raw: RankedMovie[], p: number) => others_(raw).slice(allLoaded ? p * size : 0, allLoaded ? (p + 1) * size : PAGE);
  const rowItems = pageOf(related, n);
  // the film on stage is not in the row: it counts off the total only when it is one of the found films (a film
  // opened from the widened row is not), and a capped count stays a round "500+"
  const stageFound = movie !== null && related.some((r) => r.movie.id === movie.id);
  const others = found
    ? { total: found.capped ? found.total : Math.max(0, found.total - (stageFound ? 1 : 0)), capped: found.capped }
    : null;
  const target = pending ? pageOf(pending.raw, pending.n) : [];
  const forward = pending !== null && pending.n > n;
  const shownRow = !pending ? rowItems : forward ? [...rowItems, ...target] : [...target, ...rowItems];
  const sweep: Sweep | null = pending
    ? {
        from: forward ? 0 : target.length,
        to: forward ? rowItems.length : 0,
        onDone: () => {
          loadedFor.current = `${criteriaKey}|${pending.n}|${stageId}|${feedbackVersion}`;
          setRelated(pending.raw);
          setPage({ key: criteriaKey, n: pending.n });
          setPending(null);
        },
      }
    : null;
  const canNext = allLoaded
    ? (n + 1) * size < others_(related).length
    : others !== null && ((n + 1) * PAGE < others.total || Boolean(others.capped));

  return (
    <CinemaFrame>
      <div
        className="genre-bg"
        aria-hidden="true"
        style={movie?.backdrop_url || movie?.poster_url ? { backgroundImage: `url(${movie.backdrop_url ?? movie.poster_url})` } : undefined}
      />
      <FogLight tint={world?.tint ?? "#1b4a6b"} reduced={reduced} />
      <header className="genre-top">
        <Breadcrumb items={crumbs(movie, fromSearch)} />
      </header>
      {state.kind === "error" && <p className="genre-error">Couldn&apos;t load films</p>}
      {state.kind === "loading" && <p className="genre-loading">Loading …</p>}
      {movie && world && (
        <>
          <StagePanel
            movie={movie}
            world={world}
            why={stageWhy(movie, world)}
            feedback={feedbackFor(movie.id)}
            onFeedback={giveFeedback}
            onSteer={steerSession}
          />
          <div className="side-settings side-settings--genre">
            {fromSearch ? (
              <MoodSummary tags={tags} criteria={criteria} hiddenCount={hidden} />
            ) : (
              <section className="criteria-panel genre-panel" aria-label="Genre">
                <p className="genre-panel__kicker">{world.kicker}</p>
                <h2 className="genre-panel__title">{world.title}</h2>
                <p className="genre-panel__subtitle">{world.subtitle}</p>
              </section>
            )}
          </div>
          <RelatedRow
            key={n} // a new page starts at its first film
            items={shownRow}
            onSelect={select}
            label={
              !fromSearch
                ? likeLabel(rowItems.length, movie.title, world.title)
                : widenedRow
                ? widenedLabel(rowItems.filter((r) => widenedRow.exact.has(r.movie.id)).length, rowItems.length, widenedRow.label)
                : rowLabel(rowItems.length, n * PAGE + 1, others, fromSearch && rowFromSearch, hasAnyCriteria(criteria), world.title)
            }
            name={fromSearch && rowFromSearch ? "Your other matches" : fromSearch ? "Also fits your mood" : "Films like this"}
            showReasons={fromSearch && rowFromSearch}
            found={found}
            streamCheck={fromSearch && rowFromSearch && criteria.availability === "stream"}
            arrows
            bounded
            sweep={sweep}
            paging={{ size: PAGE, prev: n > 0 ? () => turn(n - 1) : null, next: canNext ? () => turn(n + 1) : null }}
          />
        </>
      )}
    </CinemaFrame>
  );
}

const PAGE = 30; // films per page of the row, as on the search page
const LIKE_THIS = 29; // films like the one on stage, opened from the homepage
const count = new Intl.NumberFormat("en-US");

/** The heading of a widened row, as on the search page: "Only 1 film matches every wish · 48 more with: …". */
export function widenedLabel(exact: number, all: number, label: string) {
  const head = exact ? `Only ${exact} ${exact === 1 ? "film matches" : "films match"} every wish` : "No other film matches every wish";
  return (
    <>
      {`${head} · ${all - exact} more with: ${label}`}
    </>
  );
}

/** The row's heading, like the search page's: how many it shows, their ranks and of how many in all
 *  ("30 more matches · 31–60 of 366"); without a total (the stage film's neighbours) just how many. */
export function rowLabel(
  n: number,
  start: number,
  others: { total: number; capped?: boolean } | null,
  fromSearch: boolean,
  hasCriteria: boolean,
  worldTitle: string,
) {
  const what = fromSearch || hasCriteria ? "more matches" : `more top-rated ${worldTitle} films`;
  if (!others) return `${n} ${what}`;
  return (
    <>
      {`${n} ${what}`}
      <span className="related-hint">
        {" "}
        · {start}–{start + n - 1} of {count.format(others.total)}
        {others.capped ? "+" : ""}
        {!fromSearch && hasCriteria ? ` in ${worldTitle}` : ""}
      </span>
    </>
  );
}

/** From the search: CineSense › Search › film. From the homepage it is another area: just CineSense › film. */
function crumbs(movie: Movie | null, fromSearch: boolean): Crumb[] {
  const out: Crumb[] = fromSearch ? [{ label: "Search", href: "/results" }] : [];
  if (movie) out.push({ label: movie.title });
  return out;
}

/** The heading of the row opened from the homepage: "29 films like Inception · in Science Fiction". */
export function likeLabel(n: number, title: string, worldTitle: string) {
  return (
    <>
      {`${n} ${n === 1 ? "film" : "films"} like ${title}`}
      <span className="related-hint"> · in {worldTitle}</span>
    </>
  );
}

/** Why the film on stage, opened from the homepage: what it shares with the film it was picked as being like, else
 *  what it is in its genre, with its rating. */
export function likeWhy(m: Movie, worldTitle: string, of: Movie | null): string {
  const rated = m.ml_rating !== null ? ` · MovieLens ${m.ml_rating.toFixed(1)}/5 from ${count.format(m.ml_rating_count)} ratings` : "";
  if (of) {
    const shared = m.top_tags.filter((t) => of.top_tags.includes(t)).slice(0, 3);
    return `Like ${of.title}${shared.length ? `: also ${shared.join(", ")}` : ""}${rated}`;
  }
  return `A top-rated ${worldTitle} film${rated}`;
}
