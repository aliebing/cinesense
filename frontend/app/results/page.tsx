"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import Breadcrumb from "@/components/nav/Breadcrumb";
import ResultList from "@/components/results/ResultList";
import AdvancedSearch from "@/components/search/AdvancedSearch";
import ExclusionsBar from "@/components/search/ExclusionsBar";
import SearchChips from "@/components/search/SearchChips";
import { type DiscoverResult, getTags, type Tag } from "@/lib/api";
import { type Criteria, patchSearchState, useSearchState } from "@/lib/searchState";
import type { Movie } from "@/lib/types";

export default function ResultsPage() {
  const router = useRouter();
  const [criteria, setCriteria] = useSearchState();
  const [tags, setTags] = useState<Tag[]>([]);
  const [hidden, setHidden] = useState(0);
  const [hiddenBy, setHiddenBy] = useState<Record<string, number> | undefined>(undefined);
  const [showAdvanced, setShowAdvanced] = useState(false);
  // a widening chosen on this page: the original criteria and what was widened (any other change ends it)
  const [widened, setWidened] = useState<{ from: Criteria; labels: string[] } | null>(null);
  const change = useCallback(
    (c: Criteria) => {
      setWidened(null);
      setCriteria(c);
    },
    [setCriteria],
  );
  const relax = (c: Criteria, label: string) => {
    setWidened((w) => ({ from: w?.from ?? criteria, labels: [...(w?.labels ?? []), label] }));
    setCriteria(c);
  };

  useEffect(() => {
    getTags().then((r) => r.ok && setTags(r.data));
  }, []);
  const onMeta = useCallback((m: Omit<DiscoverResult, "items">) => {
    setHidden(m.hidden_by_exclusion);
    setHiddenBy(m.hidden_by);
    // autocorrect: a misspelt person or title becomes the name the search found ("sandra bullok" -> "Sandra Bullock")
    const patch: Partial<Criteria> = {};
    if (m.corrected_person) patch.person = m.corrected_person;
    if (m.corrected_title) patch.title = m.corrected_title;
    if (Object.keys(patch).length) patchSearchState(patch);
  }, []);
  const open = (m: Movie) => router.push(`/world/${m.world_ids[0] ?? "suspense"}?film=${m.id}&from=search`); // the row below the stage keeps the other matches

  return (
    <CinemaFrame>
      <FogLight tint="#1b4a6b" reduced />
      <div className="results-page">
        <header className="genre-top results-top">
          <Breadcrumb items={[{ label: "Search" }]} />
        </header>
        {/* the films first, then what steers them: moods, then exclusions and filters, then the advanced search */}
        <ResultList criteria={criteria} onOpen={open} onMeta={onMeta} onRelax={relax} widened={widened} />
        <SearchChips tags={tags} criteria={criteria} onChange={change} moodOnly />
        <ExclusionsBar tags={tags} criteria={criteria} onChange={change} hiddenCount={hidden} hiddenBy={hiddenBy}>
          <button type="button" className="results-toggle" aria-expanded={showAdvanced} onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced ? "Hide advanced search ▴" : "Advanced search ▾"}
          </button>
        </ExclusionsBar>
        {showAdvanced && (
          <AdvancedSearch
            criteria={criteria}
            onSubmit={(c) => {
              change(c);
              setShowAdvanced(false);
            }}
          />
        )}
      </div>
    </CinemaFrame>
  );
}
