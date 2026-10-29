"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import HeroSlides from "@/components/atmosphere/HeroSlides";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import ChatPanel from "@/components/chat/ChatPanel";
import FilmTitles from "@/components/home/FilmTitles";
import TileRows from "@/components/home/TileRows";
import WorldLabel from "@/components/home/WorldLabel";
import { getHome, type ApiResult } from "@/lib/api";
import type { HomeData, Movie } from "@/lib/types";
import { useReducedMotion } from "@/lib/useReducedMotion";

export default function HomePage() {
  const router = useRouter();
  const reduced = useReducedMotion();
  const [result, setResult] = useState<ApiResult<HomeData> | null>(null);
  const [active, setActive] = useState(0);
  const [variedSpeed, setVariedSpeed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getHome().then((r) => {
      if (!cancelled) setResult(r);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const data = result?.ok ? result.data : null;
  const worlds = useMemo(() => data?.worlds ?? [], [data]);
  const images = useMemo(() => {
    const out: Record<string, string | null> = {};
    for (const w of worlds) {
      const m = data?.tiles.find((t) => t.world_ids.includes(w.id));
      out[w.id] = m?.backdrop_url ?? m?.poster_url ?? null;
    }
    return out;
  }, [worlds, data]);
  const advance = useCallback(() => setActive((i) => (worlds.length ? (i + 1) % worlds.length : 0)), [worlds.length]);
  const world = worlds[active];

  const openMovie = (m: Movie) => router.push(`/welt/${m.world_ids[0]}?film=${m.id}`);

  return (
    <CinemaFrame>
      <HeroSlides worlds={worlds} images={images} activeIndex={active} onAdvance={advance} />
      <FogLight tint={world?.tint ?? "#1b4a6b"} reduced={reduced} />
      <div className="home-shade" aria-hidden="true" />

      <header className="home-top">
        <span className="home-logo">CineSense</span>
        <nav aria-label="Hauptnavigation" className="home-nav">
          <span>🎬 Im Kino</span> · <span>📺 Im Stream</span> · <span aria-label="Profil">👤</span>
        </nav>
      </header>
      <button type="button" className="tempo-toggle" onClick={() => setVariedSpeed((v) => !v)}>
        Tempo: {variedSpeed ? "unterschiedlich" : "gleichmäßig"}
      </button>

      <main className="home-center">
        <h1 className="home-claim">
          <span>Don&apos;t choose a movie.</span>
          <em>Choose a feeling.</em>
        </h1>
        <p className="home-sub">Sag mir, worauf du heute Lust hast.</p>
        <ChatPanel mode="static" />
        {result && !result.ok && <p className="home-error">Filme konnten nicht geladen werden</p>}
      </main>

      {data && <FilmTitles titles={data.titles} />}
      {data && (
        <div className="home-rows">
          <TileRows movies={data.tiles} rows={4} onSelect={openMovie} variedSpeed={variedSpeed} />
        </div>
      )}
      {world && <WorldLabel world={world} href={`/welt/${world.id}`} />}
    </CinemaFrame>
  );
}
