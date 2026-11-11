"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import FogLight from "@/components/atmosphere/FogLight";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import Breadcrumb from "@/components/nav/Breadcrumb";
import ResultList from "@/components/results/ResultList";
import AdvancedSearch from "@/components/search/AdvancedSearch";
import ExclusionsBar from "@/components/search/ExclusionsBar";
import SearchChips from "@/components/search/SearchChips";
import { type DiscoverResult, getTags, type Tag } from "@/lib/api";
import { type Criteria, patchSearchState, useSearchState } from "@/lib/searchState";
import { useForwardScroll } from "@/lib/useForwardScroll";
import type { Movie } from "@/lib/types";

export default function ResultsPage() {
  const router = useRouter();
  const [criteria, setCriteria] = useSearchState();
  const [tags, setTags] = useState<Tag[]>([]);
  const pageRef = useRef<HTMLDivElement>(null);
  useForwardScroll(pageRef); // the wheel over the curtains and bars scrolls the films too
  const [hidden, setHidden] = useState(0);
  const [hiddenBy, setHiddenBy] = useState<Record<string, number> | undefined>(undefined);
  // a widening chosen on this page: the original criteria and what was widened (any other change ends it)
  // closed → open; closing: the box slides out first, then it is gone
  const [advanced, setAdvanced] = useState<"closed" | "open" | "closing">("closed");
  // Next keeps a left page alive and shows it again on return: leaving it closes the box, so the page always comes
  // back with the advanced search folded away
  useEffect(() => () => setAdvanced("closed"), []);
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
  const tagNames = useMemo(() => Object.fromEntries(tags.map((t) => [t.idx, t.tag])), [tags]);
  const open = (m: Movie) => router.push(`/world/${m.world_ids[0] ?? "suspense"}?film=${m.id}&from=search`); // the row below the stage keeps the other matches

  return (
    <CinemaFrame>
      <FogLight tint="#1b4a6b" reduced />
      <div className="results-page" ref={pageRef}>
        <header className="genre-top results-top">
          <Breadcrumb items={[{ label: "Search" }]} />
        </header>
        {/* what steers the search on top (filters, moods, the advanced search on the right), the films below */}
        <ExclusionsBar tags={tags} criteria={criteria} onChange={change} hiddenCount={hidden} hiddenBy={hiddenBy} />
        <SearchChips tags={tags} criteria={criteria} onChange={change} moodOnly />
        {/* optional: the button on the right slides the advanced search in to its left, in the same row */}
        <div className="results-adv">
          <button
            type="button"
            className="results-toggle"
            aria-expanded={advanced === "open"}
            onClick={() => setAdvanced((a) => (a === "open" ? "closing" : "open"))}
          >
            {advanced === "open" ? "Close ▸" : "◂ Advanced search"}
          </button>
          {advanced !== "closed" && (
            <div className={`results-adv__box ${advanced === "closing" ? "is-closing" : ""}`} onAnimationEnd={() => setAdvanced((a) => (a === "closing" ? "closed" : a))}>
              <AdvancedSearch
                bar
                criteria={criteria}
                onSubmit={(c) => {
                  change(c);
                  setAdvanced("closing");
                }}
              />
            </div>
          )}
        </div>
        <div className="results-films">
          <ResultList criteria={criteria} onOpen={open} onMeta={onMeta} onRelax={relax} widened={widened} tagNames={tagNames} />
        </div>
      </div>
    </CinemaFrame>
  );
}
