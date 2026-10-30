"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import HeroSlides from "@/components/atmosphere/HeroSlides";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import ChatPanel from "@/components/chat/ChatPanel";
import ProfilePanel from "@/components/profile/ProfilePanel";
import FilmTitles from "@/components/home/FilmTitles";
import TileRows, { visibleWorlds } from "@/components/home/TileRows";
import WorldLabel from "@/components/home/WorldLabel";
import SearchChips from "@/components/search/SearchChips";
import { getHome, getTags, type ApiResult, type Tag } from "@/lib/api";
import { hasAnyCriteria, useSearchState } from "@/lib/searchState";
import type { HomeData } from "@/lib/types";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { useIsNarrow, useReducedMotion } from "@/lib/useReducedMotion";

export default function HomePage() {
  const router = useRouter();
  const reduced = useReducedMotion();
  const narrow = useIsNarrow();
  const [result, setResult] = useState<ApiResult<HomeData> | null>(null);
  const [active, setActive] = useState(0);
  const [variedSpeed, setVariedSpeed] = useState(false);
  const { activeId } = useActiveTrailer();
  const [criteria, setCriteria] = useSearchState();
  const [tags, setTags] = useState<Tag[]>([]);

  useEffect(() => {
    let cancelled = false;
    getHome().then((r) => {
      if (!cancelled) setResult(r);
    });
    getTags().then((r) => {
      if (!cancelled && r.ok) setTags(r.data);
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
      // text-free backdrops only: title art would clash with the claim and the chat
      const m = (data?.rows[w.id] ?? []).find((t) => t.backdrop_url);
      out[w.id] = m?.backdrop_url ?? null;
    }
    return out;
  }, [worlds, data]);
  const worldIds = useMemo(() => worlds.map((w) => w.id), [worlds]);
  const advance = useCallback(() => setActive((i) => (worlds.length ? (i + 1) % worlds.length : 0)), [worlds.length]);
  const world = worlds[active];

  const [showProfile, setShowProfile] = useState(false);
  const browse = (availability: "cinema" | "stream") => {
    setCriteria({ ...criteria, availability });
    router.push("/results");
  };

  return (
    <CinemaFrame>
      <HeroSlides worlds={worlds} images={images} activeIndex={active} onAdvance={advance} paused={activeId !== null} />
      <FogLight tint={world?.tint ?? "#1b4a6b"} reduced={reduced || narrow} />
      <div className="home-shade" aria-hidden="true" />

      <header className="home-top">
        <span className="home-logo">CineSense</span>
        <nav aria-label="Main navigation" className="home-nav">
          <Link href="/results">🔍 Search</Link> ·{" "}
          <button type="button" onClick={() => browse("cinema")}>
            🎬 In cinemas
          </button>{" "}
          ·{" "}
          <button type="button" onClick={() => browse("stream")}>
            📺 Streaming
          </button>{" "}
          · <Link href="/credits">Credits</Link> ·{" "}
          <button type="button" aria-label="Profile" aria-expanded={showProfile} onClick={() => setShowProfile((v) => !v)}>
            👤
          </button>
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
        <ChatPanel mode="live" horrorIdx={tags.find((t) => t.tag === "horror")?.idx ?? null} />
        {result && !result.ok && <p className="home-error">Couldn&apos;t load films</p>}
      </main>
      <div className="side-settings">
        <SearchChips tags={tags} criteria={criteria} onChange={setCriteria}>
          {hasAnyCriteria(criteria) && (
            <button type="button" className="chat-results" onClick={() => router.push("/results")}>
              Show results →
            </button>
          )}
        </SearchChips>
      </div>

      {data && !narrow && <FilmTitles titles={data.titles} />}
      {data && (
        <div className="home-rows">
          <TileRows
            rows={visibleWorlds(active, worlds, narrow ? 1 : 4).map((w) => ({ world: w, movies: data.rows[w.id] ?? [] }))}
            variedSpeed={variedSpeed}
            worldOrder={worldIds}
          />
        </div>
      )}
      {world && <WorldLabel world={world} href={`/world/${world.id}`} />}
      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
    </CinemaFrame>
  );
}
