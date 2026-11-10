"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import HeroSlides from "@/components/atmosphere/HeroSlides";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import ChatPanel from "@/components/chat/ChatPanel";
import Breadcrumb from "@/components/nav/Breadcrumb";
import ProfilePanel from "@/components/profile/ProfilePanel";
import FilmTitles from "@/components/home/FilmTitles";
import TileRows from "@/components/home/TileRows";
import WorldLabel from "@/components/home/WorldLabel";
import SearchChips from "@/components/search/SearchChips";
import { getHome, getTags, type ApiResult, type Tag } from "@/lib/api";
import { hasAnyCriteria, useSearchState } from "@/lib/searchState";
import type { HomeData, HomeTile, MoodWorld, TileRow } from "@/lib/types";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { useIsNarrow, useReducedMotion } from "@/lib/useReducedMotion";

const TITLES_PER_MOOD = 6;

/** Without a search: the top-rated films of the mood on screen (the hero world) in `count` rows running against each
 *  other, its films dealt out in turn. The rows keep their ids when the mood changes, so they run on and only their
 *  films change (no new rows, no jump). */
export function moodRows(world: MoodWorld | undefined, data: HomeData | null, count: number): TileRow[] {
  if (!world || !data) return [];
  const films = data.rows[world.id] ?? [];
  return Array.from({ length: count }, (_, r) => ({
    world: { ...world, id: `mood-${r}` },
    movies: films.filter((_, i) => i % count === r),
  })).filter((row) => row.movies.length > 0);
}

/** The homepage. `initial`: the rows the server already fetched (app/page.tsx); without them the browser asks. */
export default function HomePage({ initial = null }: { initial?: HomeData | null }) {
  const router = useRouter();
  const reduced = useReducedMotion();
  const narrow = useIsNarrow();
  const [result, setResult] = useState<ApiResult<HomeData> | null>(initial ? { ok: true, data: initial } : null);
  const hasInitial = initial !== null;
  const [active, setActive] = useState(0);
  const { activeId } = useActiveTrailer();
  const [criteria, setCriteria] = useSearchState();
  const [tags, setTags] = useState<Tag[]>([]);

  useEffect(() => {
    let cancelled = false;
    if (!hasInitial)
      getHome().then((r) => {
        if (!cancelled) setResult(r);
      });
    getTags().then((r) => {
      if (!cancelled && r.ok) setTags(r.data);
    });
    return () => {
      cancelled = true;
    };
  }, [hasInitial]);

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
  // the titles that drift over the stage belong to the mood on screen, like its picture and its rows
  const moodTitles = useMemo(() => (world && data ? (data.rows[world.id] ?? []).slice(0, TITLES_PER_MOOD).map((t) => t.title) : []), [world, data]);

  const [showProfile, setShowProfile] = useState(false);
  const browse = (availability: "cinema" | "stream") => {
    setCriteria({ ...criteria, availability });
    router.push("/results");
  };
  const openMovie = (m: HomeTile) => router.push(`/world/${m.world_ids[0]}?film=${m.id}`);
  // always the mood on screen: its top-rated films in two equal rows (one on a narrow screen); a search is shown on
  // the search page, not here
  const rows = moodRows(world, data, narrow ? 1 : 2);

  return (
    <CinemaFrame>
      <HeroSlides worlds={worlds} images={images} activeIndex={active} onAdvance={advance} paused={activeId !== null} />
      <FogLight tint={world?.tint ?? "#1b4a6b"} reduced={reduced || narrow} />
      <div className="home-shade" aria-hidden="true" />

      <header className="home-top">
        <Breadcrumb items={[{ label: "Home" }]} />
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

      {data && !narrow && <FilmTitles titles={moodTitles} />}
      {rows.length > 0 && (
        <div className="home-rows">
          <TileRows rows={rows} onSelect={openMovie} worldOrder={worldIds} />
        </div>
      )}
      {world && <WorldLabel world={world} href={`/world/${world.id}`} />}
      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
    </CinemaFrame>
  );
}
