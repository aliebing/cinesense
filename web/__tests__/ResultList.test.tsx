import { render, screen } from "@testing-library/react";
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

it("shows the total, never claims 'all', and runs the best matches in one row", async () => {
  search.mockResolvedValue({ ok: true, data: { items: sampleRanked(20), total: 250, hidden_by_exclusion: 3, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/250 matches in the CineSense catalogue/)).toBeInTheDocument();
  expect(screen.getByText(/the best 20/)).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Results" })).toBeInTheDocument();
  expect(search.mock.calls[0][2]).toBe(48);
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
});

it("opens a film on click", async () => {
  const onOpen = vi.fn();
  search.mockResolvedValue({ ok: true, data: { items: sampleRanked(2), total: 2, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={onOpen} />);
  await userEvent.click((await screen.findAllByRole("button", { name: "Demo-Film 01, 90% match" }))[0]);
  expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: "demo-01" }));
});

it("shows reasons and the streaming state on cards", async () => {
  const items = sampleRanked(1).map((r) => ({ ...r, reasons: ["dark 91%", "streaming on Netflix"] }));
  search.mockResolvedValue({ ok: true, data: { items, total: 1, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect((await screen.findAllByText("dark 91% · streaming on Netflix"))[0]).toBeInTheDocument();
});
