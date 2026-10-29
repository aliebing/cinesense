"use client";

import Link from "next/link";
import { notFound, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import ChatDrawer from "@/components/genre/ChatDrawer";
import RelatedRow from "@/components/genre/RelatedRow";
import StagePanel from "@/components/genre/StagePanel";
import SearchChips from "@/components/search/SearchChips";
import {
  discover,
  getMovie,
  getProfile,
  getRelated,
  getTags,
  getWorldMovies,
  getWorlds,
  type ProfileSummary,
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

export default function GenreView({ worldId, filmId }: { worldId: string; filmId: string | null }) {
  const router = useRouter();
  const reduced = useReducedMotion();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [related, setRelated] = useState<RankedMovie[]>([]);
  const [criteria, setCriteria] = useSearchState();
  const [tags, setTags] = useState<Tag[]>([]);
  const [hidden, setHidden] = useState(0);
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
    const t = setTimeout(() => {
      if (hasAnyCriteria(active)) {
        // the chip bar re-ranks the row within this world
        discover({ ...active, world_id: worldId }, 0, 24).then((r) => {
          if (cancelled) return;
          setRelated(r.ok ? r.data.items : []);
          setHidden(r.ok ? r.data.hidden_by_exclusion : 0);
        });
      } else {
        getRelated(stageId, worldId).then((r) => {
          if (cancelled) return;
          setRelated(r.ok ? r.data : []);
          setHidden(0);
        });
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [stageId, worldId, criteriaKey, feedbackVersion]);

  if (state.kind === "not_found") {
    notFound();
    return null;
  }

  const select = (m: Movie) => {
    if (state.kind !== "ready") return;
    setStageReasons({ id: m.id, reasons: related.find((r) => r.movie.id === m.id)?.reasons ?? [] });
    setState({ ...state, movie: m });
    router.replace(`/world/${worldId}?film=${m.id}`, { scroll: false });
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
        <Link href="/">CineSense &nbsp;← Back to home</Link>
        {world && <span className="genre-world">World: {world.title}</span>}
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
          <div className="genre-chips">
            <SearchChips tags={tags} criteria={criteria} onChange={setCriteria} hiddenCount={hidden} />
          </div>
          <RelatedRow items={related.filter((r) => r.movie.id !== movie.id)} onSelect={select} />
          <ChatDrawer horrorIdx={tags.find((t) => t.tag === "horror")?.idx ?? null} />
        </>
      )}
    </CinemaFrame>
  );
}
