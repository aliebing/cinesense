"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import ResultList from "@/components/results/ResultList";
import AdvancedSearch from "@/components/search/AdvancedSearch";
import SearchChips from "@/components/search/SearchChips";
import { getTags, type Tag } from "@/lib/api";
import { useSearchState } from "@/lib/searchState";
import type { Movie } from "@/lib/types";

export default function ResultsPage() {
  const router = useRouter();
  const [criteria, setCriteria] = useSearchState();
  const [tags, setTags] = useState<Tag[]>([]);
  const [hidden, setHidden] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    getTags().then((r) => r.ok && setTags(r.data));
  }, []);
  const onMeta = useCallback((m: { hidden_by_exclusion: number }) => setHidden(m.hidden_by_exclusion), []);
  const open = (m: Movie) => router.push(`/world/${m.world_ids[0] ?? "suspense"}?film=${m.id}`);

  return (
    <CinemaFrame>
      <FogLight tint="#1b4a6b" reduced />
      <div className="results-page">
        <header className="genre-top results-top">
          <Link href="/">CineSense &nbsp;← Back to home</Link>
          <button type="button" className="results-toggle" onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced ? "Hide advanced search" : "Advanced search"}
          </button>
        </header>
        {showAdvanced && (
          <AdvancedSearch
            criteria={criteria}
            onSubmit={(c) => {
              setCriteria(c);
              setShowAdvanced(false);
            }}
          />
        )}
        <SearchChips tags={tags} criteria={criteria} onChange={setCriteria} hiddenCount={hidden} />
        <ResultList criteria={criteria} onOpen={open} onMeta={onMeta} />
      </div>
    </CinemaFrame>
  );
}
