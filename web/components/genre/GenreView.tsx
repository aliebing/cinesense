"use client";

import Link from "next/link";
import { notFound, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import ChatDrawer from "@/components/genre/ChatDrawer";
import RelatedRow from "@/components/genre/RelatedRow";
import StagePanel from "@/components/genre/StagePanel";
import { getMovie, getRelated, getWorldMovies, getWorlds } from "@/lib/api";
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
    getRelated(stageId, worldId).then((r) => {
      if (!cancelled) setRelated(r.ok ? r.data : []);
    });
    return () => {
      cancelled = true;
    };
  }, [stageId, worldId]);

  if (state.kind === "not_found") {
    notFound();
    return null;
  }

  const select = (m: Movie) => {
    if (state.kind !== "ready") return;
    setState({ ...state, movie: m });
    router.replace(`/welt/${worldId}?film=${m.id}`, { scroll: false });
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
        <Link href="/">CineSense &nbsp;← Zurück zur Startseite</Link>
        {world && <span className="genre-world">Welt: {world.title_de}</span>}
      </header>
      {state.kind === "error" && <p className="genre-error">Filme konnten nicht geladen werden</p>}
      {state.kind === "loading" && <p className="genre-loading">Lädt …</p>}
      {movie && world && (
        <>
          <StagePanel movie={movie} world={world} why={`Gut bewertet in der Welt „${world.title_de}“`} />
          <RelatedRow items={related.filter((r) => r.movie.id !== movie.id)} onSelect={select} />
          <ChatDrawer />
        </>
      )}
    </CinemaFrame>
  );
}
