import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

const inspectTurn = vi.fn();
vi.mock("@/lib/api", () => ({ inspectTurn: (...a: unknown[]) => inspectTurn(...a) }));

import TechPage from "@/app/tech/page";

it("shows the reply, criteria, tools, cost and the films as plain text", async () => {
  inspectTurn.mockResolvedValue({
    ok: true,
    data: {
      reply: "These fit because…",
      picks: 1,
      results: [
        { id: "a", title: "Deadpool", year: 2016, match_percent: 94, score: 0.94, reasons: ["funny 98%"], genres: ["Action"], worlds: ["action"], directors: ["Tim Miller"], cast: ["Ryan Reynolds"], runtime_min: 108, ml_rating: 3.9, ml_rating_count: 50000, overview: "A mercenary…" },
        { id: "b", title: "Kick-Ass", year: 2010, match_percent: 90, score: 0.9, reasons: [], genres: [], worlds: [], directors: [], cast: [], runtime_min: null, ml_rating: null, ml_rating_count: null, overview: null },
      ],
      criteria: { tags: [] },
      criteria_summary: "tags: funny (prefer, 6)",
      tags: [{ tag: "funny", weight: 6, mode: "prefer" }],
      proposals: [],
      tools: [{ name: "set_mood_tags", args: { tags: ["funny"] }, result: "ok" }],
      prompts: { agent: "You are CineSense", explain: "You explain", explain_input: "Wish: x" },
      model: "anthropic/claude-haiku-5.5",
      usage: { input_tokens: 1200, output_tokens: 300 },
      cost_usd: 0.00027,
      latency_s: 6.2,
      rounds: 1,
      grounding_fallback: false,
      grounding_reason: [],
    },
  });
  render(<TechPage />);
  await userEvent.type(screen.getByLabelText("Message"), "something funny");
  await userEvent.click(screen.getByRole("button", { name: "send" }));
  expect(await screen.findByText("These fit because…")).toBeInTheDocument();
  expect(screen.getByText("set_mood_tags")).toBeInTheDocument();
  expect(screen.getByText("$0.00027")).toBeInTheDocument();
  expect(screen.getByText("1200")).toBeInTheDocument();
  expect(screen.getByText(/Deadpool/).closest("li")).toHaveClass("is-pick");
  expect(screen.getByText(/Kick-Ass/).closest("li")).not.toHaveClass("is-pick");
  expect(document.querySelector("img, iframe, video")).toBeNull();
  expect(inspectTurn.mock.calls[0][1]).toBe("something funny");
});
