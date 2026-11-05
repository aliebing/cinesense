import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import ScenarioList from "@/components/eval/ScenarioList";
import { modelLabel, runLabel } from "@/components/eval/labels";
import type { EvalScenario } from "@/lib/api";

function scenario(id: string, passed: boolean, extra: Partial<EvalScenario> = {}): EvalScenario {
  return {
    id,
    category: "mood",
    failure: null,
    turns: ["Something funny", "rather from the 90s"],
    tools_called: ["new_search", "set_filters"],
    tools_per_turn: [["new_search"], ["set_filters"]],
    reply: `Reply of ${id}`,
    results: ["Shrek"],
    passed,
    error: null,
    checks: {
      tools: { ok: passed, why: passed ? [] : ["should not call ['new_search']"], applies: true },
      guarded: { ok: true, why: [], applies: false },
    },
    judge: { score: 4, reason: "Fits." },
    latency_s: 9.2,
    ...extra,
  };
}

it("labels runs and models in plain words", () => {
  expect(runLabel("2026-11-05_1554")).toBe("5 Nov 2026, 15:54");
  expect(modelLabel("anthropic/claude-haiku-5.5")).toBe("Claude Haiku 5.5");
});

it("lists scenarios with only the checks that apply, filters the failed ones and opens the turn", async () => {
  render(<ScenarioList scenarios={[scenario("ok-01", true), scenario("bad-01", false)]} rows={[]} />);
  expect(screen.getByText("ok-01")).toBeInTheDocument();
  expect(screen.getAllByTitle("Right tools")[0]).toHaveTextContent("✓ 1 check"); // the guard check does not apply here

  await userEvent.click(screen.getByRole("button", { name: "Failed 1" }));
  expect(screen.queryByText("ok-01")).not.toBeInTheDocument();
  const row = screen.getByText("bad-01").closest("li")!;
  await userEvent.click(within(row).getByText("bad-01"));
  expect(within(row).getByText(/should not call/, { selector: "p" })).toBeInTheDocument();
  expect(within(row).getByText(/→ set_filters/)).toBeInTheDocument(); // tools per turn
});
