import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/admin/visitors" }));

const getVisitors = vi.fn();
const getVisitorTurn = vi.fn();
vi.mock("@/lib/api", () => ({
  getVisitors: (...a: unknown[]) => getVisitors(...a),
  getVisitorTurn: (...a: unknown[]) => getVisitorTurn(...a),
}));

import AdminNav from "@/components/admin/AdminNav";
import VisitorsPage from "@/app/admin/visitors/page";

const turn = (id: number, message: string) => ({
  id,
  ts: "2026-11-05T14:54:00+00:00",
  scope: "chat",
  visitor: "a1b2c3d4e5f6",
  thread: "t",
  message,
  films: 5,
  tools: ["set_mood_tags"],
  grounding_fallback: id === 1,
  guarded: false,
  input_tokens: 1000,
  output_tokens: 200,
  cost_usd: 0.0012,
  duration_ms: 8200,
  error: null,
});

it("the nav links the three admin pages and marks the current one", () => {
  render(<AdminNav />);
  const nav = screen.getByRole("navigation", { name: "Admin pages" });
  expect([...nav.querySelectorAll("a")].map((a) => a.textContent)).toEqual(["Tech", "Visitors", "Evaluation"]);
  expect(screen.getByRole("link", { name: "Visitors" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "Tech" })).not.toHaveAttribute("aria-current");
});

it("lists the logged turns with sums and opens one with its conversation", async () => {
  getVisitors.mockResolvedValue({
    ok: true,
    data: { items: [turn(2, "rather from the 90s"), turn(1, "funny films")], total: 2, sums: { count: 2, cost_usd: 0.0024, avg_duration_ms: 8200, visitors: 1 } },
  });
  getVisitorTurn.mockImplementation(async (id: number) => ({
    ok: true,
    data: {
      ...turn(id, id === 2 ? "rather from the 90s" : "funny films"),
      reply: `Reply ${id}`,
      criteria: {},
      criteria_summary: "tags: funny (prefer, 6)",
      films: [{ title: "Speed", year: 1994, match: 88 }],
      tools: [{ name: "set_filters", args: { year_from: 1990 } }],
      relaxed: [],
      grounding_reason: [],
      model: "anthropic/claude-haiku-5.5",
      conversation: id === 2 ? [{ id: 1, ts: "2026-11-05T14:53:00+00:00", message: "funny films" }] : [],
    },
  }));
  render(<VisitorsPage />);
  expect(await screen.findByText("rather from the 90s")).toBeInTheDocument();
  expect(getVisitors).toHaveBeenCalledWith(null, 0, 50);
  expect(screen.getByText(/2 turns/)).toHaveTextContent("2 turns from 1 visitor in the chat · $0.0024 · 8.2 s on average");
  expect(screen.getByText("template")).toBeInTheDocument();
  const detail = await screen.findByRole("complementary", { name: "Turn details" });
  expect(detail).toHaveTextContent("Reply 2");
  expect(detail).toHaveTextContent("Earlier in this conversation");
  expect(detail).toHaveTextContent("Speed (1994)");
  expect(detail).toHaveTextContent('set_filters({"year_from":1990})');

  await userEvent.click(screen.getByRole("button", { name: "Show turn 1" }));
  await waitFor(() => expect(screen.getByRole("complementary", { name: "Turn details" })).toHaveTextContent("Reply 1"));

  await userEvent.click(screen.getByRole("button", { name: "Tech view" }));
  expect(getVisitors).toHaveBeenLastCalledWith("tech", 0, 50);
});
