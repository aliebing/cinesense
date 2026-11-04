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
  expect(screen.getByText("directed by Tim Miller · with Ryan Reynolds")).toBeInTheDocument();
  expect(screen.queryByText(/with \?|directed by \?/)).toBeNull(); // Kick-Ass has no credits: no line
  expect(document.querySelector("img, iframe, video")).toBeNull();
  expect(inspectTurn.mock.calls[0][1]).toBe("something funny");
});

it("lists the films simply: a linked title and a short description; the numbers fold away", async () => {
  const long = "A mercenary with a twisted sense of humour hunts the man who nearly destroyed his life, ".repeat(4).trim();
  inspectTurn.mockResolvedValue({
    ok: true,
    data: {
      reply: "r", picks: 1,
      results: [
        { id: "ml-1", title: "Deadpool", year: 2016, match_percent: 94, score: 0.94, reasons: ["funny 98%"], genres: ["Action"], worlds: ["comedy"], directors: [], cast: [], runtime_min: null, ml_rating: null, ml_rating_count: null, overview: long },
      ],
      criteria: { tags: [] }, criteria_summary: "", tags: [], proposals: [], tools: [], prompts: {},
      model: "m", usage: {}, cost_usd: 0, latency_s: 1, rounds: 1, grounding_fallback: false, grounding_reason: [],
    },
  });
  render(<TechPage />);
  await userEvent.type(screen.getByLabelText("Message"), "x");
  await userEvent.click(screen.getByRole("button", { name: "send" }));
  const link = await screen.findByRole("link", { name: "Deadpool (2016)" });
  expect(link).toHaveAttribute("href", "/world/comedy?film=ml-1"); // no IMDb id: our own film page
  const short = screen.getByTestId("tech-short");
  expect(short.textContent!.length).toBeLessThanOrEqual(181);
  expect(short.textContent!.endsWith("…")).toBe(true);
  expect(screen.getByText(/94% match/).closest("details")).not.toBeNull();
});

it("links a title to its German IMDb page when the IMDb id is known", async () => {
  inspectTurn.mockResolvedValue({
    ok: true,
    data: {
      reply: "r", picks: 1,
      results: [
        { id: "ml-139385", imdb_id: "tt1663202", title: "The Revenant", year: 2015, match_percent: 90, score: 0.9, reasons: [], genres: [], worlds: ["suspense"], directors: [], cast: [], runtime_min: null, ml_rating: null, ml_rating_count: null, overview: null },
      ],
      criteria: { tags: [] }, criteria_summary: "", tags: [], proposals: [], tools: [], prompts: {},
      model: "m", usage: {}, cost_usd: 0, latency_s: 1, rounds: 1, grounding_fallback: false, grounding_reason: [],
    },
  });
  render(<TechPage />);
  await userEvent.type(screen.getByLabelText("Message"), "x");
  await userEvent.click(screen.getByRole("button", { name: "send" }));
  const link = await screen.findByRole("link", { name: "The Revenant (2015)" });
  expect(link).toHaveAttribute("href", "https://www.imdb.com/de/title/tt1663202/");
  expect(link).toHaveAttribute("target", "_blank");
});

it("shows the limit message when the assistant's daily limit is reached", async () => {
  inspectTurn.mockResolvedValue({ ok: false, error: "limited", message: "You've reached today's limit for the assistant." });
  render(<TechPage />);
  await userEvent.type(screen.getByLabelText("Message"), "x");
  await userEvent.click(screen.getByRole("button", { name: "send" }));
  expect(await screen.findByText("You've reached today's limit for the assistant.")).toBeInTheDocument();
});
