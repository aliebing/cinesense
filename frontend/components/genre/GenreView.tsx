"use client";

import { stageWhyText } from "@/lib/why";
import { notFound, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import RelatedRow, { type Sweep } from "@/components/genre/RelatedRow";
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
    if (!stageId || !active.tags?.length) return;
    let cancelled = false;
    fitMovie(stageId, active).then((r) => {
      if (!cancelled && r.ok) setStageFit({ id: stageId, key: criteriaKey, fit: r.data });
    });
    return () => {
      cancelled = true;
    };
  }, [stageId, criteriaKey]);
  const n = page.key === criteriaKey ? page.n : 0;
  // one page of the row: the search's matches (opened from the search) or the world's films ranked by the chips
  // (or by rating without any); one film more than a page, as the stage film may be among them
  const fetchPage = useCallback(
    async (active: Criteria, pageNo: number) => {
      const useSearch = fromSearch && hasAnyCriteria(active);
      const r = useSearch
        ? await search(active, pageNo * PAGE, PAGE + 1)
        : await discover({ ...active, world_id: worldId }, pageNo * PAGE, PAGE + 1);
      if (!r.ok) return null;
      return { items: r.data.items, total: r.data.total, capped: Boolean(r.data.total_capped), hidden: r.data.hidden_by_exclusion, useSearch };
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
      getRelated(stageId, worldId).then((r) => {
        if (cancelled) return;
        setRelated(r.ok ? r.data : []);
        setFound(null);
        setRowFromSearch(false);
        setHidden(0);
        loadedFor.current = loadKey;
      });
    const t = setTimeout(async () => {
      const p = await fetchPage(active, n);
      if (cancelled) return;
      if (!p || (n === 0 && !p.items.some((x) => x.movie.id !== stageId))) return loadRelated();
      const onStage = p.items.find((x) => x.movie.id === stageId);
      if (onStage && p.useSearch) setStageReasons((s) => s ?? { id: onStage.movie.id, reasons: onStage.reasons });
      setRelated(p.items);
      setFound({ total: p.total, capped: p.capped });
      setRowFromSearch(p.useSearch);
      setHidden(p.hidden);
      loadedFor.current = loadKey;
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [stageId, worldId, criteriaKey, n, loadKey, fetchPage]);
  const turn = async (to: number) => {
    if (pending) return;
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
    const reasons = stageReasons?.id === m.id ? stageReasons.reasons : [];
    const fit = stageFit?.id === m.id && stageFit.key === criteriaKey ? stageFit.fit : null;
    return stageWhyText(m, w.title, reasons, fit);
  };

  const world = state.kind === "ready" ? state.world : null;
  const movie = state.kind === "ready" ? state.movie : null;
  const pageOf = (raw: RankedMovie[]) => (movie ? raw.filter((r) => r.movie.id !== movie.id).slice(0, PAGE) : []);
  const rowItems = pageOf(related);
  // the film on stage is one of the found ones, but not in the row (a capped count stays a round "500+")
  const others = found ? { total: found.capped ? found.total : Math.max(0, found.total - 1), capped: found.capped } : null;
  const target = pending ? pageOf(pending.raw) : [];
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
  const canNext = others !== null && ((n + 1) * PAGE < others.total || Boolean(others.capped));

  return (
    <CinemaFrame>
      <div
        className="genre-bg"
        aria-hidden="true"
        style={movie?.backdrop_url || movie?.poster_url ? { backgroundImage: `url(${movie.backdrop_url ?? movie.poster_url})` } : undefined}
      />
      <FogLight tint={world?.tint ?? "#1b4a6b"} reduced={reduced} />
      <header className="genre-top">
        <Breadcrumb items={crumbs(movie)} />
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
            <MoodSummary tags={tags} criteria={criteria} hiddenCount={hidden} />
          </div>
          <RelatedRow
            key={n} // a new page starts at its first film
            items={shownRow}
            onSelect={select}
            label={rowLabel(rowItems.length, n * PAGE + 1, others, fromSearch && rowFromSearch, hasAnyCriteria(criteria), world.title)}
            name={fromSearch && rowFromSearch ? "Your other matches" : "Also fits your mood"}
            showReasons={fromSearch && rowFromSearch}
            found={found}
            streamCheck={fromSearch && rowFromSearch && criteria.availability === "stream"}
            arrows
            sweep={sweep}
            paging={{ size: PAGE, prev: n > 0 ? () => turn(n - 1) : null, next: canNext ? () => turn(n + 1) : null }}
          />
        </>
      )}
    </CinemaFrame>
  );
}

const PAGE = 30; // films per page of the row, as on the search page
const count = new Intl.NumberFormat("en-US");

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

/** CineSense › Search › film: the search is always one step back (a world crumb would just repeat the brand). */
function crumbs(movie: Movie | null): Crumb[] {
  const out: Crumb[] = [{ label: "Search", href: "/results" }]; // always: the search is one step back from any film
  if (movie) out.push({ label: movie.title });
  return out;
}
