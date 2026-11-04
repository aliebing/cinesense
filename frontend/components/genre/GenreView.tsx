"use client";

import { notFound, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import RelatedRow from "@/components/genre/RelatedRow";
import StagePanel from "@/components/genre/StagePanel";
import Breadcrumb, { type Crumb } from "@/components/nav/Breadcrumb";
import {
  discover,
  getMovie,
  getProfile,
  getRelated,
  getTags,
  getWorldMovies,
  getWorlds,
  type ProfileSummary,
  search,
  sendFeedback,
  type Tag,
} from "@/lib/api";
import { hasAnyCriteria, steer, useSearchState } from "@/lib/searchState";
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
  // the shared search state: no settings panel here (moods are edited on the home and results pages), but it
  // still ranks the row, and ⚡ / 😂 add to it
  const [criteria, setCriteria] = useSearchState();
  const [tags, setTags] = useState<Tag[]>([]);
  const [rowFromSearch, setRowFromSearch] = useState(fromSearch);
  const criteriaKey = JSON.stringify(criteria);

  const [profile, setProfile] = useState<ProfileSummary | null>(null);
  const [feedbackVersion, setFeedbackVersion] = useState(0);
  const feedbackPending = useRef(false);
  const [stageReasons, setStageReasons] = useState<{ id: string; reasons: string[] } | null>(null);

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
    if (!stageId) return;
    let cancelled = false;
    const active = JSON.parse(criteriaKey);
    // the stage film's own neighbours: also the fallback when a search leaves nothing else to show
    // (a title search finds just the film on stage, and the row would stay empty)
    const loadRelated = () =>
      getRelated(stageId, worldId).then((r) => {
        if (cancelled) return;
        setRelated(r.ok ? r.data : []);
        setRowFromSearch(false);
      });
    const others = (items: RankedMovie[]) => items.some((x) => x.movie.id !== stageId);
    const t = setTimeout(() => {
      if (fromSearch && hasAnyCriteria(active)) {
        search(active, 0, 48).then((r) => {
          if (cancelled) return;
          const items = r.ok ? r.data.items : [];
          const onStage = items.find((x) => x.movie.id === stageId);
          if (onStage) setStageReasons((s) => s ?? { id: onStage.movie.id, reasons: onStage.reasons });
          if (!others(items)) return loadRelated();
          setRelated(items);
          setRowFromSearch(true);
        });
      } else if (hasAnyCriteria(active)) {
        // the chip bar re-ranks the row within this world
        discover({ ...active, world_id: worldId }, 0, 24).then((r) => {
          if (cancelled) return;
          const items = r.ok ? r.data.items : [];
          if (!others(items)) return loadRelated();
          setRelated(items);
          setRowFromSearch(false);
        });
      } else {
        loadRelated();
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [stageId, worldId, criteriaKey, feedbackVersion, fromSearch]);

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
    return reasons.length ? reasons.join(" · ") : `Highly rated in the “${w.title}” world`;
  };

  const world = state.kind === "ready" ? state.world : null;
  const movie = state.kind === "ready" ? state.movie : null;

  return (
    <CinemaFrame>
      <div
        className="genre-bg"
        aria-hidden="true"
        style={movie?.backdrop_url || movie?.poster_url ? { backgroundImage: `url(${movie.backdrop_url ?? movie.poster_url})` } : undefined}
      />
      <FogLight tint={world?.tint ?? "#1b4a6b"} reduced={reduced} />
      <header className="genre-top">
        <Breadcrumb items={crumbs(world, movie, fromSearch)} />
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
          {fromSearch && rowFromSearch ? (
            <RelatedRow
              items={related.filter((r) => r.movie.id !== movie.id)}
              onSelect={select}
              label="Your other matches"
              name="Your other matches"
              showReasons
            />
          ) : (
            <RelatedRow items={related.filter((r) => r.movie.id !== movie.id)} onSelect={select} />
          )}
        </>
      )}
    </CinemaFrame>
  );
}

/** Opened from the search: Search › film; otherwise the world it belongs to › film. The world crumb leads back
 *  to the start page showing that world (/world/<id> would only put the world's top film on this stage). */
function crumbs(world: MoodWorld | null, movie: Movie | null, fromSearch: boolean): Crumb[] {
  const out: Crumb[] = fromSearch ? [{ label: "Search", href: "/results" }] : world ? [{ label: world.title, href: `/?world=${world.id}` }] : [];
  if (movie) out.push({ label: movie.title });
  return out;
}
