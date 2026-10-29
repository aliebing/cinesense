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
import { useIsNarrow, useReducedMotion } from "@/lib/useReducedMotion";

export default function HomePage() {
  const router = useRouter();
  const reduced = useReducedMotion();
  const narrow = useIsNarrow();
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

  const openMovie = (m: Movie) => router.push(`/world/${m.world_ids[0]}?film=${m.id}`);

  return (
    <CinemaFrame>
      <HeroSlides worlds={worlds} images={images} activeIndex={active} onAdvance={advance} />
      <FogLight tint={world?.tint ?? "#1b4a6b"} reduced={reduced || narrow} />
      <div className="home-shade" aria-hidden="true" />

      <header className="home-top">
        <span className="home-logo">CineSense</span>
        <nav aria-label="Main navigation" className="home-nav">
          <span>🎬 In cinemas</span> · <span>📺 Streaming</span> · <span aria-label="Profile">👤</span>
        </nav>
      </header>
      <button type="button" className="tempo-toggle" onClick={() => setVariedSpeed((v) => !v)}>
        Speed: {variedSpeed ? "varied" : "even"}
      </button>

      <main className="home-center">
        <h1 className="home-claim">
          <span>Don&apos;t choose a movie.</span>
          <em>Choose a feeling.</em>
        </h1>
        <p className="home-sub">Tell me what you’re in the mood for tonight.</p>
        <ChatPanel mode="static" />
        {result && !result.ok && <p className="home-error">Couldn&apos;t load films</p>}
      </main>

      {data && !narrow && <FilmTitles titles={data.titles} />}
      {data && (
        <div className="home-rows">
          <TileRows movies={data.tiles} rows={narrow ? 1 : 4} onSelect={openMovie} variedSpeed={variedSpeed} />
        </div>
      )}
      {world && <WorldLabel world={world} href={`/world/${world.id}`} />}
    </CinemaFrame>
  );
}
