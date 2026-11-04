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

it("nothing found with a person: says so and offers the search without that person", async () => {
  search.mockResolvedValue({ ok: true, data: { items: [], total: 0, hidden_by_exclusion: 0, extended_used: false, relaxations: [] } });
  const onRelax = vi.fn();
  const criteria = { ...emptyCriteria(), person: "qwertz uiop" };
  render(<ResultList criteria={criteria} onOpen={() => {}} onRelax={onRelax} />);
  expect(await screen.findByText("Nothing found with 👤 qwertz uiop")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Search without this person" }));
  expect(onRelax).toHaveBeenCalledWith({ ...criteria, person: null }, "without qwertz uiop");
});

it("nothing found with a title: offers the search without that title", async () => {
  search.mockResolvedValue({ ok: true, data: { items: [], total: 0, hidden_by_exclusion: 0, extended_used: false, relaxations: [] } });
  const onRelax = vi.fn();
  const criteria = { ...emptyCriteria(), title: "xyzzy" };
  render(<ResultList criteria={criteria} onOpen={() => {}} onRelax={onRelax} />);
  expect(await screen.findByText("Nothing found with 🔤 “xyzzy”")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Search without this title" }));
  expect(onRelax).toHaveBeenCalledWith({ ...criteria, title: null }, "without “xyzzy”");
});

it("a thin search says how many films match before offering to widen it", async () => {
  const wider = emptyCriteria();
  search.mockResolvedValue({
    ok: true,
    data: {
      items: sampleRanked(2),
      total: 2,
      hidden_by_exclusion: 0,
      extended_used: false,
      relaxations: [{ id: "tags-to-plot", label: "Search the mood in plots", count: 4, criteria: wider }],
    },
  });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} onRelax={() => {}} />);
  expect(await screen.findByText("Only 2 films match every wish. More with:")).toBeInTheDocument();
  expect(screen.queryByText(/Nothing matches/)).toBeNull();
});

it("shows a loading bar while results load, and dims the old row", async () => {
  let resolve: (v: unknown) => void = () => {};
  search.mockResolvedValueOnce({ ok: true, data: { items: sampleRanked(3), total: 3, hidden_by_exclusion: 0, extended_used: false } });
  const { rerender } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(screen.getByRole("progressbar", { name: "Loading results" })).toBeInTheDocument(); // first load
  await screen.findByText(/3 matches/);
  expect(screen.queryByRole("progressbar")).toBeNull();
  search.mockImplementationOnce(() => new Promise((r) => (resolve = r)));
  rerender(<ResultList criteria={{ ...emptyCriteria(), title: "x" }} onOpen={() => {}} />);
  expect(screen.getByRole("progressbar", { name: "Loading results" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Results" })).toHaveClass("is-busy");
  await waitFor(() => expect(search).toHaveBeenCalledTimes(2)); // the request starts after a short pause
  resolve({ ok: true, data: { items: sampleRanked(1), total: 1, hidden_by_exclusion: 0, extended_used: false } });
  await screen.findByText(/1 matches/);
  expect(screen.queryByRole("progressbar")).toBeNull();
});

it("shows at least the 3 best matches, and says out of how many", async () => {
  const items = sampleRanked(12).map((r, i) => ({ ...r, match_percent: 49 - i }));
  search.mockResolvedValue({ ok: true, data: { items, total: 39, hidden_by_exclusion: 0, extended_used: false } });
  const { container } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 3 best matches/)).toBeInTheDocument(); // none reaches 50%: the 3 best
  expect(screen.getByText(/out of 39 films that fit your filters/)).toBeInTheDocument();
  expect(container.querySelectorAll(".related-card")).toHaveLength(3);
  expect(search.mock.calls[0][2]).toBe(50); // at most 50
});

it("shows every film from 50% up (Sandra Bullock + action + funny: 7 of 39)", async () => {
  const percents = [71, 63, 59, 59, 57, 51, 51, 48, 48, 48];
  const items = sampleRanked(10).map((r, i) => ({ ...r, match_percent: percents[i] }));
  search.mockResolvedValue({ ok: true, data: { items, total: 39, hidden_by_exclusion: 0, extended_used: false } });
  const { container } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 7 best matches/)).toBeInTheDocument();
  expect(screen.getByText(/out of 39 films/)).toBeInTheDocument();
  const titles = new Set([...container.querySelectorAll(".related-card")].map((c) => c.getAttribute("aria-label") ?? c.textContent));
  expect(titles.size).toBe(7); // a row too long to fit loops, so its cards appear twice
});

it("another tag lowers every score, so it shows fewer films, not more (+ horror: 4)", async () => {
  const percents = [55, 55, 54, 50, 49, 49, 44, 44, 30, 22];
  const items = sampleRanked(10).map((r, i) => ({ ...r, match_percent: percents[i] }));
  search.mockResolvedValue({ ok: true, data: { items, total: 39, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 4 best matches/)).toBeInTheDocument();
});

it("a search with only a few hits just counts them", async () => {
  search.mockResolvedValue({ ok: true, data: { items: sampleRanked(3), total: 3, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/^3 matches/)).toBeInTheDocument();
  expect(screen.queryByText(/out of/)).toBeNull();
});

it("loads the next 50 when every shown film still matches, until the bar is reached", async () => {
  const page = (from: number, n: number, percent: (i: number) => number) =>
    sampleRanked(n).map((r, i) => ({ ...r, movie: { ...r.movie, id: `f-${from + i}`, title: `Film ${from + i}` }, match_percent: percent(from + i) }));
  search.mockResolvedValueOnce({ ok: true, data: { items: page(0, 50, () => 80), total: 500, hidden_by_exclusion: 0, extended_used: false } });
  search.mockResolvedValueOnce({
    ok: true,
    data: { items: page(50, 50, (i) => (i < 70 ? 60 : 40)), total: 500, hidden_by_exclusion: 0, extended_used: false },
  });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 50 best matches/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Show 50 more" }));
  expect(await screen.findByText(/The 70 best matches/)).toBeInTheDocument(); // 20 of the next 50 reach 50%
  expect(search.mock.calls[1][1]).toBe(50); // offset
  expect(screen.queryByRole("button", { name: /more/ })).toBeNull(); // below the bar: nothing more to load
});

it("offers no more button when the row already stops at the bar", async () => {
  const items = sampleRanked(10).map((r, i) => ({ ...r, match_percent: i < 5 ? 70 : 40 }));
  search.mockResolvedValue({ ok: true, data: { items, total: 500, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 5 best matches/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /more/ })).toBeNull();
});

it("says 500+ when the mood search kept only its best films", async () => {
  const items = sampleRanked(10).map((r) => ({ ...r, match_percent: 40 }));
  search.mockResolvedValue({ ok: true, data: { items, total: 500, total_capped: true, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/out of 500\+ films that fit your filters/)).toBeInTheDocument();
});
