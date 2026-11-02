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

it("offers ways to widen a search that finds too little", async () => {
  const onRelax = vi.fn();
  const wider = { ...emptyCriteria(), availability: "any" as const };
  search.mockResolvedValue({
    ok: true,
    data: {
      items: [],
      total: 0,
      hidden_by_exclusion: 0,
      extended_used: false,
      relaxations: [{ id: "availability", label: "Not only in cinemas", count: 12, criteria: wider }],
    },
  });
  render(<ResultList criteria={{ ...emptyCriteria(), availability: "cinema" }} onOpen={() => {}} onRelax={onRelax} />);
  expect(await screen.findByText("No matches in the CineSense catalogue")).toBeInTheDocument();
  expect(screen.getByText("Nothing matches every wish. Try:")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Not only in cinemas · 12 films" }));
  expect(onRelax).toHaveBeenCalledWith(wider, "Not only in cinemas");
});

it("shows no relaxation buttons without onRelax", async () => {
  search.mockResolvedValue({
    ok: true,
    data: {
      items: sampleRanked(1),
      total: 1,
      hidden_by_exclusion: 0,
      extended_used: false,
      relaxations: [{ id: "runtime", label: "Allow up to 90 min", count: 2, criteria: emptyCriteria() }],
    },
  });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/1 matches in the CineSense catalogue/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Allow up to 90 min/ })).toBeNull();
});

it("sends what the search was widened from, says so, and marks misses on cards", async () => {
  const items = sampleRanked(1).map((r) => ({ ...r, misses: ["not in cinemas"] }));
  search.mockResolvedValue({ ok: true, data: { items, total: 1, hidden_by_exclusion: 0, extended_used: false } });
  const from = { ...emptyCriteria(), availability: "cinema" as const };
  render(
    <ResultList criteria={emptyCriteria()} onOpen={() => {}} widened={{ from, labels: ["Not only in cinemas"] }} />,
  );
  expect(await screen.findByText(/Widened: Not only in cinemas/)).toBeInTheDocument();
  expect(search.mock.calls[0][3]).toEqual(from);
  expect((await screen.findAllByText("≠ not in cinemas"))[0]).toBeInTheDocument();
});

it("passes the label along when a relaxation is chosen", async () => {
  const onRelax = vi.fn();
  const wider = { ...emptyCriteria(), max_runtime_min: 90 };
  search.mockResolvedValue({
    ok: true,
    data: {
      items: [],
      total: 0,
      hidden_by_exclusion: 0,
      extended_used: false,
      relaxations: [{ id: "runtime", label: "Allow up to 90 min", count: 2, criteria: wider }],
    },
  });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} onRelax={onRelax} />);
  await userEvent.click(await screen.findByRole("button", { name: "Allow up to 90 min · 2 films" }));
  expect(onRelax).toHaveBeenCalledWith(wider, "Allow up to 90 min");
});

it("hides old relaxation buttons as soon as the criteria change", async () => {
  const wider = { ...emptyCriteria(), max_runtime_min: 90 };
  search.mockResolvedValueOnce({
    ok: true,
    data: {
      items: [],
      total: 0,
      hidden_by_exclusion: 0,
      extended_used: false,
      relaxations: [{ id: "runtime", label: "Allow up to 90 min", count: 2, criteria: wider }],
    },
  });
  search.mockReturnValueOnce(new Promise(() => {})); // the next search is still loading
  const { rerender } = render(
    <ResultList criteria={{ ...emptyCriteria(), max_runtime_min: 60 }} onOpen={() => {}} onRelax={() => {}} />,
  );
  expect(await screen.findByRole("button", { name: "Allow up to 90 min · 2 films" })).toBeInTheDocument();
  rerender(<ResultList criteria={wider} onOpen={() => {}} onRelax={() => {}} />);
  expect(screen.queryByRole("button", { name: /Allow up to 90 min/ })).toBeNull();
});
