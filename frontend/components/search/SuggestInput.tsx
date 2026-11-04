"use client";

import { useEffect, useState } from "react";
import type { Suggestion } from "@/lib/api";

export const MIN_CHARS = 4; // suggestions from the 4th letter on

type Props = {
  id: string;
  label: string;
  placeholder?: string;
  value: string;
  /** typing: the text is not a pick (yet) */
  onType: (text: string) => void;
  /** a suggestion was clicked: this value is taken */
  onPick: (value: string) => void;
  picked: boolean;
  load: (q: string) => Promise<Suggestion[]>;
};

/** A text field that suggests catalogue names while typing; only a clicked suggestion counts as chosen. */
export default function SuggestInput({ id, label, placeholder, value, onType, onPick, picked, load }: Props) {
  const [found, setFound] = useState<{ q: string; items: Suggestion[] }>({ q: "", items: [] });
  const q = value.trim();
  const wanted = !picked && q.length >= MIN_CHARS;

  useEffect(() => {
    if (!wanted) return;
    let cancelled = false;
    const t = setTimeout(() => {
      load(q).then((items) => {
        if (!cancelled) setFound({ q, items });
      });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q, wanted, load]);

  const items = wanted && found.q === q ? found.items : [];
  return (
    <label className="suggest">
      {label}
      <input
        id={id}
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={items.length > 0}
        aria-controls={`${id}-suggestions`}
        onChange={(e) => onType(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && setFound({ q: "", items: [] })}
      />
      {items.length > 0 && (
        <ul id={`${id}-suggestions`} className="suggest__list" role="listbox" aria-label={`${label} suggestions`}>
          {items.map((s) => (
            <li
              key={s.value}
              role="option"
              aria-selected={false}
              tabIndex={0}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onPick(s.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), onPick(s.value))}
            >
              {s.label}
            </li>
          ))}
        </ul>
      )}
    </label>
  );
}
