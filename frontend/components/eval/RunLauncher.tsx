"use client";

import { useMemo, useState } from "react";
import { money } from "@/components/admin/format";
import type { EvalOptions } from "@/lib/api";

const PRESET_LABELS: Record<string, string> = {
  quick: "Quick: one of each main kind",
  medium: "Broader mix",
  all: "Every scenario",
};

/** Model with its token prices, a selection of scenarios, the estimated cost, and the start button. */
export default function RunLauncher({
  options,
  busy,
  onStart,
}: {
  options: EvalOptions;
  busy: boolean;
  onStart: (model: string, ids: string[]) => void;
}) {
  const [model, setModel] = useState(options.default_model);
  const [preset, setPreset] = useState<string>("quick");
  const [custom, setCustom] = useState<Set<string>>(() => new Set(options.presets.quick));
  const ids = preset === "custom" ? options.scenarios.filter((s) => custom.has(s.id)).map((s) => s.id) : options.presets[preset];

  const estimate = useMemo(() => {
    const m = options.models.find((x) => x.id === model);
    if (!m || m.agent_per_scenario_usd == null || options.judge.per_call_usd == null) return null;
    const chosen = new Set(ids);
    const compared = options.scenarios.filter((s) => chosen.has(s.id) && s.compared).length;
    return ids.length * m.agent_per_scenario_usd + (ids.length + 3 * compared) * options.judge.per_call_usd;
  }, [options, model, ids]);

  const toggle = (id: string) =>
    setCustom((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <form
      className="evl"
      onSubmit={(e) => {
        e.preventDefault();
        if (ids.length && !busy) onStart(model, ids);
      }}
    >
      <fieldset className="evl-models">
        <legend>Agent model</legend>
        {options.models.map((m) => (
          <label key={m.id} className={m.id === model ? "evl-model is-chosen" : "evl-model"}>
            <input type="radio" name="model" value={m.id} checked={m.id === model} onChange={() => setModel(m.id)} />
            <span className="evl-model-name">{m.label}</span>
            <span className="evl-price">
              ${m.input_per_million} in · ${m.output_per_million} out
              <small>per million tokens{m.price_source === "table" ? " (saved price, OpenRouter unreachable)" : ""}</small>
            </span>
            {m.agent_per_scenario_usd != null && (
              <span className="evl-per">≈ {money(m.agent_per_scenario_usd)} per scenario</span>
            )}
          </label>
        ))}
        <p className="evl-judge">
          The judge stays {options.judge.label} (${options.judge.input_per_million} in · $
          {options.judge.output_per_million} out per million tokens), so scores compare across runs.
        </p>
      </fieldset>

      <fieldset className="evl-pick">
        <legend>Scenarios</legend>
        {[...Object.keys(options.presets), "custom"].map((p) => (
          <label key={p}>
            <input type="radio" name="preset" value={p} checked={preset === p} onChange={() => setPreset(p)} />{" "}
            {p === "custom" ? "Choose yourself" : `${PRESET_LABELS[p] ?? p} (${options.presets[p].length})`}
          </label>
        ))}
        {preset === "custom" ? (
          <ul className="evl-list">
            {options.scenarios.map((s) => (
              <li key={s.id}>
                <label>
                  <input type="checkbox" checked={custom.has(s.id)} onChange={() => toggle(s.id)} /> <b>{s.id}</b>{" "}
                  {s.turns.join(" → ")}
                </label>
              </li>
            ))}
          </ul>
        ) : (
          <p className="evl-chosen">{ids.join(", ")}</p>
        )}
      </fieldset>

      <div className="evl-go">
        <button type="submit" disabled={busy || ids.length === 0}>
          Start run with {ids.length} scenario{ids.length === 1 ? "" : "s"}
        </button>
        {estimate != null && (
          <span className="admin-lead">
            About {money(estimate)} including the judge, estimated from the tokens of the last full run
            {options.estimate_basis ? ` (${options.estimate_basis.split("/").pop()})` : ""}.
          </span>
        )}
      </div>
    </form>
  );
}
