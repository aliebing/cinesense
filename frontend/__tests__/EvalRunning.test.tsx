import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import LiveRun from "@/components/eval/LiveRun";
import RunLauncher from "@/components/eval/RunLauncher";
import RunTable from "@/components/eval/RunTable";
import type { EvalLive, EvalOptions, EvalRunOverview } from "@/lib/api";

const options: EvalOptions = {
  models: [
    { id: "anthropic/claude-haiku-5.5", label: "Claude Haiku 5.5", input_per_million: 0.1, output_per_million: 0.5, price_source: "openrouter", agent_per_scenario_usd: 0.002 },
    { id: "openai/gpt-5.6-terra", label: "GPT-5.6 Terra", input_per_million: 2, output_per_million: 12, price_source: "table", agent_per_scenario_usd: 0.03 },
  ],
  default_model: "anthropic/claude-haiku-5.5",
  judge: { id: "anthropic/claude-sonnet-5.5", label: "Claude Sonnet 5.5", input_per_million: 2, output_per_million: 10, price_source: "openrouter", per_call_usd: 0.001 },
  estimate_basis: "anthropic/claude-haiku-5.5",
  scenarios: [
    { id: "mood-02", category: "mood", turns: ["feel-good comedy"], compared: true },
    { id: "inject-01", category: "injection", turns: ["Ignore all previous instructions"], compared: false },
    { id: "facts-01", category: "facts", turns: ["Tell me about Alien"], compared: false },
  ],
  presets: { quick: ["mood-02", "inject-01"], all: ["mood-02", "inject-01", "facts-01"] },
};

it("shows prices per model, estimates the cost and starts with the chosen model and scenarios", async () => {
  const onStart = vi.fn();
  render(<RunLauncher options={options} busy={false} onStart={onStart} />);
  expect(screen.getByText(/\$0.1 in · \$0.5 out/)).toBeInTheDocument();
  expect(screen.getByText(/saved price, OpenRouter unreachable/)).toBeInTheDocument();
  // 2 scenarios x $0.002 + (2 + 3 x 1 compared) judge calls x $0.001 = $0.009
  expect(screen.getByText(/About \$0.0090 including the judge/)).toBeInTheDocument();

  await userEvent.click(screen.getByRole("radio", { name: /GPT-5.6 Terra/ }));
  await userEvent.click(screen.getByRole("radio", { name: /Every scenario/ }));
  await userEvent.click(screen.getByRole("button", { name: "Start run with 3 scenarios" }));
  expect(onStart).toHaveBeenCalledWith("openai/gpt-5.6-terra", ["mood-02", "inject-01", "facts-01"]);

  await userEvent.click(screen.getByRole("radio", { name: /Choose yourself/ }));
  await userEvent.click(screen.getByRole("checkbox", { name: /facts-01/ }));
  expect(screen.getByRole("button", { name: "Start run with 3 scenarios" })).toBeInTheDocument();
});

it("cannot start while a run is going", () => {
  render(<RunLauncher options={options} busy onStart={vi.fn()} />);
  expect(screen.getByRole("button", { name: /Start run/ })).toBeDisabled();
});

it("shows progress, the scenario being asked and each result as it comes", async () => {
  const live: EvalLive = {
    status: "running",
    model: "openai/gpt-5.6-luna",
    total: 6,
    done: 1,
    passed: 0,
    cost_usd: 0.0017,
    current: { id: "like-01", turns: ["Something like Interstellar"] },
    phase: "scenarios",
    results: [
      { id: "mood-02", category: "mood", turns: ["feel-good comedy"], passed: false, reply: "Try Paddington.", results: ["Paddington"], judge: { score: 4, reason: "ok" }, latency_s: 7.2, cost_usd: 0.0017, error: null, failed_checks: ["tools"], grounding_fallback: false },
    ],
  };
  const onStop = vi.fn();
  render(<LiveRun live={live} onStop={onStop} onShow={vi.fn()} />);
  expect(screen.getByText(/Running: 1 of 6 scenarios with GPT-5.6 Luna/)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "1");
  expect(screen.getByText(/Asking/)).toHaveTextContent("Asking like-01: “Something like Interstellar”");
  expect(screen.getByText("Failed: Right tools")).toBeInTheDocument();
  expect(screen.getByText(/judge 4\/5/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Stop after this scenario" }));
  expect(onStop).toHaveBeenCalled();
});

it("lists the last ten runs, newest first, marking selections and runs started here", async () => {
  const run = (i: number, extra: Partial<EvalRunOverview> = {}): EvalRunOverview => ({
    run: `2026-11-${String(i).padStart(2, "0")}_1000`,
    scenarios: 63,
    scenarios_total: 63,
    passed: 60,
    grounding_raw: 0.9,
    agent_judge: 3.7,
    ranker_judge: {},
    model: "anthropic/claude-haiku-5.5",
    cost_usd: 0.4,
    stopped: false,
    source: "local",
    ...extra,
  });
  const runs = [...Array.from({ length: 11 }, (_, i) => run(i + 1)), run(12, { scenarios: 6, passed: 5, source: "server" })];
  const onSelect = vi.fn();
  render(<RunTable runs={runs} selected="2026-11-12_1000" onSelect={onSelect} />);
  const rows = screen.getAllByRole("row").slice(1);
  expect(rows).toHaveLength(10);
  expect(rows[0]).toHaveTextContent("12 Nov 2026, 10:00started hereClaude Haiku 5.56 of 635 / 6");
  expect(rows[1]).toHaveTextContent("all 63");
  await userEvent.click(screen.getByRole("button", { name: "11 Nov 2026, 10:00" }));
  expect(onSelect).toHaveBeenCalledWith("2026-11-11_1000");
});
