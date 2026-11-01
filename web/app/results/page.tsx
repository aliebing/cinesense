"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import BackHome from "@/components/nav/BackHome";
import Breadcrumb from "@/components/nav/Breadcrumb";
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
  const open = (m: Movie) => router.push(`/world/${m.world_ids[0] ?? "suspense"}?film=${m.id}&from=search`); // the row below the stage keeps the other matches

  return (
    <CinemaFrame>
      <FogLight tint="#1b4a6b" reduced />
      <div className="results-page">
        <header className="genre-top results-top">
          <Breadcrumb items={[{ label: "Search" }]} />
          <div className="results-actions">
            <button type="button" className="results-toggle" onClick={() => setShowAdvanced((v) => !v)}>
              {showAdvanced ? "Hide advanced search" : "Advanced search"}
            </button>
            <BackHome />
          </div>
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
