import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import ResultList from "@/components/results/ResultList";
import { emptyCriteria } from "@/lib/searchState";
import { mockMatchMedia, sampleRanked } from "./fixtures";

const search = vi.fn();
vi.mock("@/lib/api", () => ({ search: (...a: unknown[]) => search(...a) }));

beforeEach(() => {
  search.mockReset();
  mockMatchMedia(() => false);
});

it("shows the total, never claims 'all', and loads more", async () => {
  const page1 = sampleRanked(20);
  const page2 = sampleRanked(25).slice(20).map((r) => ({ ...r, movie: { ...r.movie, id: `p2-${r.movie.id}` } }));
  search
    .mockResolvedValueOnce({ ok: true, data: { items: page1, total: 25, hidden_by_exclusion: 3, extended_used: false } })
    .mockResolvedValueOnce({ ok: true, data: { items: page2, total: 25, hidden_by_exclusion: 3, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText("25 matches in the CineSense catalogue")).toBeInTheDocument();
  expect(screen.getAllByTestId("result-card")).toHaveLength(20);
  await userEvent.click(screen.getByRole("button", { name: "Load more" }));
  await waitFor(() => expect(screen.getAllByTestId("result-card")).toHaveLength(25));
  expect(search.mock.calls[1][1]).toBe(20);
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
});

it("shows reasons and the streaming state on cards", async () => {
  const items = sampleRanked(1).map((r) => ({ ...r, reasons: ["dark 91%", "streaming on Netflix"] }));
  search.mockResolvedValue({ ok: true, data: { items, total: 1, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText("dark 91% · streaming on Netflix")).toBeInTheDocument();
});
