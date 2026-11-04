"use client";

import { useState, type FormEvent } from "react";
import type { Criteria } from "@/lib/searchState";

/** Title / actor-director / year / kind search; "extended" reaches beyond the catalogue (newer films). */
export default function AdvancedSearch({ criteria, onSubmit }: { criteria: Criteria; onSubmit: (c: Criteria) => void }) {
  const [title, setTitle] = useState(criteria.title ?? "");
  const [person, setPerson] = useState(criteria.person ?? "");
  const [role, setRole] = useState(criteria.person_role);
  const [yearFrom, setYearFrom] = useState(criteria.year_from?.toString() ?? "");
  const [yearTo, setYearTo] = useState(criteria.year_to?.toString() ?? "");
  const [kind, setKind] = useState(criteria.kind);
  const [extended, setExtended] = useState(criteria.extended);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const year = (v: string) => (v.trim() && /^\d{4}$/.test(v.trim()) ? Number(v.trim()) : null);
    onSubmit({
      ...criteria,
      title: title.trim() || null,
      person: person.trim() || null,
      person_role: role,
      year_from: year(yearFrom),
      year_to: year(yearTo),
      kind,
      extended,
    });
  };

  return (
    <form className="advanced-search" onSubmit={submit} aria-label="Advanced search">
      <label>
        Title
        <input id="adv-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="typos are fine" />
      </label>
      <label>
        Actor or director
        <input id="adv-person" value={person} onChange={(e) => setPerson(e.target.value)} placeholder="e.g. Sandra Hüller" />
      </label>
      <label>
        Role
        <select id="adv-role" value={role} onChange={(e) => setRole(e.target.value as Criteria["person_role"])}>
          <option value="any">Any</option>
          <option value="cast">Actor</option>
          <option value="director">Director</option>
        </select>
      </label>
      <label>
        From year
        <input id="adv-from" inputMode="numeric" value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} />
      </label>
      <label>
        To year
        <input id="adv-to" inputMode="numeric" value={yearTo} onChange={(e) => setYearTo(e.target.value)} />
      </label>
      <label>
        Kind
        <select id="adv-kind" value={kind} onChange={(e) => setKind(e.target.value as Criteria["kind"])}>
          <option value="any">Films &amp; documentaries</option>
          <option value="film">Feature films</option>
          <option value="documentary">Documentaries</option>
        </select>
      </label>
      <label className="advanced-search__check">
        <input id="adv-extended" type="checkbox" checked={extended} onChange={(e) => setExtended(e.target.checked)} />
        Extended search (more and newer films, slower)
      </label>
      <button type="submit">Search</button>
    </form>
  );
}
