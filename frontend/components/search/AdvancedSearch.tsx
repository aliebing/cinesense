"use client";

import { useCallback, useState, type FormEvent } from "react";
import SuggestInput from "@/components/search/SuggestInput";
import { suggest } from "@/lib/api";
import type { Criteria } from "@/lib/searchState";

const ROLES: { value: Criteria["person_role"]; label: string }[] = [
  { value: "any", label: "Any" },
  { value: "cast", label: "Actor" },
  { value: "director", label: "Director" },
];
const KINDS: { value: Criteria["kind"]; label: string }[] = [
  { value: "any", label: "All" },
  { value: "film", label: "Feature films" },
  { value: "documentary", label: "Documentaries" },
];

const FIRST_FILM_YEAR = 1888;

/** The year range as numbers (empty = open), or what is wrong with it and in which field. */
export function checkYears(
  fromText: string,
  toText: string,
  lastYear = new Date().getFullYear() + 5,
): { from: number | null; to: number | null } | { error: string; field: "from" | "to" } {
  const parse = (text: string, field: "from" | "to") => {
    const t = text.trim();
    if (!t) return null;
    if (!/^\d{4}$/.test(t)) return { error: "Enter years as four digits, e.g. 1994", field };
    const n = Number(t);
    if (n < FIRST_FILM_YEAR || n > lastYear) return { error: `Years between ${FIRST_FILM_YEAR} and ${lastYear}`, field };
    return n;
  };
  const from = parse(fromText, "from");
  if (from !== null && typeof from === "object") return from;
  const to = parse(toText, "to");
  if (to !== null && typeof to === "object") return to;
  if (from !== null && to !== null && from > to) return { error: "'From year' is after 'To year'", field: "from" };
  return { from, to };
}

/** A labelled switch: every choice visible, the current one highlighted (the mood panel's Prefer / Must look). */
function Choice<T extends string>({ label, options, value, onChange }: { label: string; options: { value: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="adv-field">
      <span>{label}</span>
      <div className="crit__modes adv-switch" role="group" aria-label={label}>
        {options.map((o) => (
          <button key={o.value} type="button" className="crit__mode" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Title / actor-director / year / kind search; "extended" reaches beyond the catalogue (newer films). */
export default function AdvancedSearch({ criteria, onSubmit }: { criteria: Criteria; onSubmit: (c: Criteria) => void }) {
  const [title, setTitle] = useState(criteria.title ?? "");
  const [person, setPerson] = useState(criteria.person ?? "");
  // a title or name counts only when picked from the suggestions (what is already set counts as picked)
  const [titlePicked, setTitlePicked] = useState(Boolean(criteria.title));
  const [personPicked, setPersonPicked] = useState(Boolean(criteria.person));
  const [hint, setHint] = useState<string | null>(null);
  const [badYear, setBadYear] = useState<"from" | "to" | null>(null);
  const [role, setRole] = useState(criteria.person_role);
  const [yearFrom, setYearFrom] = useState(criteria.year_from?.toString() ?? "");
  const [yearTo, setYearTo] = useState(criteria.year_to?.toString() ?? "");
  const [kind, setKind] = useState(criteria.kind);
  const [extended, setExtended] = useState(criteria.extended);
  const loadTitles = useCallback((q: string) => suggest("title", q).then((r) => (r.ok ? r.data : [])), []);
  const loadPeople = useCallback((q: string) => suggest("person", q, role).then((r) => (r.ok ? r.data : [])), [role]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    // typed but not picked: only the extended search (newer films, not in the suggestions) takes free text
    if (!extended && title.trim() && !titlePicked) return setHint("Pick a title from the suggestions");
    if (!extended && person.trim() && !personPicked) return setHint("Pick a name from the suggestions");
    // a year that is not a real year is pointed out, not silently dropped
    const years = checkYears(yearFrom, yearTo);
    if ("error" in years) {
      setBadYear(years.field);
      return setHint(years.error);
    }
    const { from, to } = years;
    setBadYear(null);
    setHint(null);
    onSubmit({
      ...criteria,
      title: title.trim() || null,
      person: person.trim() || null,
      person_role: role,
      year_from: from,
      year_to: to,
      kind,
      extended,
    });
  };

  return (
    <form className="advanced-search" onSubmit={submit} aria-label="Advanced search">
      <SuggestInput
        id="adv-title"
        label="Title"
        placeholder="type 4 letters for suggestions"
        value={title}
        picked={titlePicked}
        onType={(t) => {
          setTitle(t);
          setTitlePicked(false);
        }}
        onPick={(t) => {
          setTitle(t);
          setTitlePicked(true);
          setHint(null);
        }}
        load={loadTitles}
      />
      <SuggestInput
        id="adv-person"
        label="Actor or director"
        placeholder="e.g. Sandra Hüller"
        value={person}
        picked={personPicked}
        onType={(t) => {
          setPerson(t);
          setPersonPicked(false);
        }}
        onPick={(t) => {
          setPerson(t);
          setPersonPicked(true);
          setHint(null);
        }}
        load={loadPeople}
      />
      <Choice label="Role" options={ROLES} value={role} onChange={setRole} />
      <label>
        From year
        <input id="adv-from" inputMode="numeric" placeholder="e.g. 1990" aria-invalid={badYear === "from"} value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} />
      </label>
      <label>
        To year
        <input id="adv-to" inputMode="numeric" placeholder="e.g. 1999" aria-invalid={badYear === "to"} value={yearTo} onChange={(e) => setYearTo(e.target.value)} />
      </label>
      <Choice label="Kind" options={KINDS} value={kind} onChange={setKind} />
      <label className="advanced-search__check">
        <input id="adv-extended" type="checkbox" checked={extended} onChange={(e) => setExtended(e.target.checked)} />
        Extended search (more and newer films, slower)
      </label>
      <button type="submit">Search</button>
      {hint && (
        <p className="advanced-search__hint" role="alert">
          {hint}
        </p>
      )}
    </form>
  );
}
