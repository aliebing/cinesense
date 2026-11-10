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
  expect((await screen.findAllByText("Strong on your moods: dark (91%) · streaming on Netflix"))[0]).toBeInTheDocument();
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
  expect(await screen.findByText("1 film found")).toBeInTheDocument();
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

const films = (from: number, n: number) =>
  sampleRanked(n).map((r, i) => ({ ...r, movie: { ...r.movie, id: `w-${from + i}`, title: `Wide ${from + i}` }, match_percent: 60 }));

it("too few films for every wish: the row below shows the least intrusive widening, the search stays as it is", async () => {
  const onRelax = vi.fn();
  const plot = { ...emptyCriteria(), plot_query: "space" };
  const original = { ...emptyCriteria(), year_from: 1990, year_to: 1999 };
  search.mockImplementation((c: { plot_query?: string | null }) =>
    Promise.resolve(
      c.plot_query
        ? { ok: true, data: { items: films(0, 5), total: 5, hidden_by_exclusion: 0, extended_used: false } }
        : {
            ok: true,
            data: {
              items: sampleRanked(2),
              total: 2,
              hidden_by_exclusion: 0,
              extended_used: false,
              relaxations: [
                { id: "runtime", label: "Allow up to 120 min", count: 2, criteria: emptyCriteria() }, // too few: skipped
                { id: "tags-to-plot", label: "Search the mood in plots", count: 12, criteria: plot },
              ],
            },
          },
    ),
  );
  const { container } = render(<ResultList criteria={original} onOpen={() => {}} onRelax={onRelax} />);
  expect(await screen.findByText(/Only 2 films match every wish · 5 more with: Search the mood in plots/)).toBeInTheDocument();
  expect(search.mock.calls[1][0]).toEqual(plot);
  expect(search.mock.calls[1][3]).toEqual(original); // marks what each widened film misses
  expect(container.querySelectorAll(".best .related-card")).toHaveLength(2);
  expect(screen.queryByRole("button", { name: /Search the mood in plots/ })).toBeNull(); // information, not a button
  expect(onRelax).not.toHaveBeenCalled(); // the user's search is left alone
});

it("no film for every wish: says so, and the widened films fill the row", async () => {
  const wider = { ...emptyCriteria(), availability: "any" as const };
  search.mockImplementation((c: { availability?: string }) =>
    Promise.resolve(
      c.availability === "any"
        ? { ok: true, data: { items: films(0, 4), total: 4, hidden_by_exclusion: 0, extended_used: false } }
        : {
            ok: true,
            data: {
              items: [],
              total: 0,
              hidden_by_exclusion: 0,
              extended_used: false,
              relaxations: [{ id: "availability", label: "Not only in cinemas", count: 12, criteria: wider }],
            },
          },
    ),
  );
  render(<ResultList criteria={{ ...emptyCriteria(), availability: "cinema" }} onOpen={() => {}} />);
  expect(await screen.findByText("No film matches every wish")).toBeInTheDocument();
  expect(screen.getByText(/No film matches every wish · 4 more with: Not only in cinemas/)).toBeInTheDocument();
});

it("shows a loading bar while results load, and dims the old row", async () => {
  let resolve: (v: unknown) => void = () => {};
  search.mockResolvedValueOnce({ ok: true, data: { items: sampleRanked(3), total: 3, hidden_by_exclusion: 0, extended_used: false } });
  const { rerender } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(screen.getByRole("progressbar", { name: "Loading results" })).toBeInTheDocument(); // first load
  await screen.findByText("3 films found");
  expect(screen.queryByRole("progressbar")).toBeNull();
  search.mockImplementationOnce(() => new Promise((r) => (resolve = r)));
  rerender(<ResultList criteria={{ ...emptyCriteria(), title: "x" }} onOpen={() => {}} />);
  expect(screen.getByRole("progressbar", { name: "Loading results" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Best matches" })).toHaveClass("is-busy");
  await waitFor(() => expect(search).toHaveBeenCalledTimes(2)); // the request starts after a short pause
  resolve({ ok: true, data: { items: sampleRanked(1), total: 1, hidden_by_exclusion: 0, extended_used: false } });
  await screen.findByText("1 film found");
  expect(screen.queryByRole("progressbar")).toBeNull();
});

it("shows at least the 3 best matches, and says how many were found", async () => {
  const items = sampleRanked(12).map((r, i) => ({ ...r, match_percent: 49 - i }));
  search.mockResolvedValue({ ok: true, data: { items, total: 39, hidden_by_exclusion: 0, extended_used: false } });
  const { container } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 3 best matches/)).toBeInTheDocument(); // none reaches 50%: the 3 best
  expect(screen.getByText("No film matches well · the 3 closest of 39 films searched")).toHaveClass("related-count");
  expect(container.querySelectorAll(".best .related-card")).toHaveLength(3);
  expect(screen.getByText("9 weaker matches (below 50%)")).toBeInTheDocument(); // the rest, said honestly
  expect(search.mock.calls[0][2]).toBe(50); // at most 50
});

it("shows up to 6 films from 70% in front, with why, and the films from 50% in the running row below", async () => {
  const percents = [95, 88, 81, 77, 72, 69, 66, 61, 58, 50];
  const items = sampleRanked(10).map((r, i) => ({ ...r, match_percent: percents[i], reasons: i === 0 ? ["dark 95%"] : [] }));
  search.mockResolvedValue({ ok: true, data: { items, total: 39, hidden_by_exclusion: 0, extended_used: false } });
  const { container } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 5 best matches/)).toBeInTheDocument();
  expect(container.querySelectorAll(".best .related-card")).toHaveLength(5);
  expect(screen.getByText("Strong on your moods: dark (95%)")).toHaveClass("best-why");
  expect(screen.getByText("5 more matches from 50%")).toBeInTheDocument(); // few strong films: the row starts at 50%
  expect(screen.getByText(/6–10 of 10/)).toBeInTheDocument(); // their ranks, and every film above the bar
  expect(screen.queryByRole("button", { name: "Previous 30" })).toBeNull(); // nothing more here: no arrows at all
  expect(screen.queryByRole("button", { name: "Next 30" })).toBeNull();
  const more = container.querySelectorAll(".results-more-row .related-card");
  expect(new Set([...more].map((c) => c.getAttribute("aria-label"))).size).toBe(5);
});

it("never more than 6 in front, the other strong films run in the row below", async () => {
  const items = sampleRanked(12).map((r) => ({ ...r, match_percent: 85 }));
  search.mockResolvedValue({ ok: true, data: { items, total: 12, hidden_by_exclusion: 0, extended_used: false } });
  const { container } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 6 best matches/)).toBeInTheDocument();
  const more = container.querySelectorAll(".results-more-row .related-card");
  expect(new Set([...more].map((c) => c.getAttribute("aria-label"))).size).toBe(6);
});

it("a weak search still shows its 3 best, and the rest as weaker matches below (+ horror lowers every score)", async () => {
  const percents = [55, 55, 54, 49, 49, 44, 44, 30, 22, 20];
  const items = sampleRanked(10).map((r, i) => ({ ...r, match_percent: percents[i] }));
  search.mockResolvedValue({ ok: true, data: { items, total: 39, hidden_by_exclusion: 0, extended_used: false } });
  const { container } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 3 best matches/)).toBeInTheDocument();
  expect(container.querySelector(".results-more-row")).not.toBeNull();
  expect(screen.getByText("7 weaker matches (below 50%)")).toBeInTheDocument();
});

it("a search with only a few hits just counts them", async () => {
  search.mockResolvedValue({ ok: true, data: { items: sampleRanked(3), total: 3, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText("3 films found")).toBeInTheDocument();
  expect(screen.getByText(/All matches/)).toBeInTheDocument();
});

it("the « » arrows page the running row by 30, load the next 50 from the API when needed, and back", async () => {
  const page = (from: number, n: number, percent: (i: number) => number) =>
    sampleRanked(n).map((r, i) => ({ ...r, movie: { ...r.movie, id: `f-${from + i}`, title: `Film ${from + i}` }, match_percent: percent(from + i) }));
  search.mockResolvedValueOnce({ ok: true, data: { items: page(0, 50, () => 80), total: 500, hidden_by_exclusion: 0, extended_used: false } });
  let resolve: (v: unknown) => void = () => {};
  search.mockImplementationOnce(() => new Promise((r) => (resolve = r)));
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 6 best matches/)).toBeInTheDocument();
  expect(screen.getByText("30 more matches from 70%")).toBeInTheDocument(); // many strong films: from 70%
  expect(screen.getByText(/7–36 of 50\+/)).toBeInTheDocument(); // more may follow from the API
  expect(screen.queryByRole("button", { name: /Next 20|Previous 20/ })).toBeNull(); // no separate page buttons
  expect(screen.queryByRole("button", { name: "Previous 30" })).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "Next 30" })); // only 12 loaded behind: load first
  expect(screen.getByRole("progressbar", { name: "Loading results" })).toBeInTheDocument();
  resolve({ ok: true, data: { items: page(50, 50, (i) => (i < 70 ? 72 : 65)), total: 500, hidden_by_exclusion: 0, extended_used: false } });
  expect(await screen.findByText(/37–66 of 70/)).toBeInTheDocument(); // 70 films from the 70% floor up in all
  expect(search.mock.calls[1][1]).toBe(50); // offset
  await userEvent.click(screen.getByRole("button", { name: "Next 30" }));
  expect(await screen.findByText(/67–70 of 70/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Next 30" })).toBeNull(); // below the bar: nothing further
  expect(search).toHaveBeenCalledTimes(2);
  await userEvent.click(screen.getByRole("button", { name: "Previous 30" }));
  expect(await screen.findByText(/37–66 of 70/)).toBeInTheDocument();
  expect(screen.getByText(/The 6 best matches/)).toBeInTheDocument(); // the best stay in front throughout
});

it("offers no more button when the row already stops at the bar", async () => {
  const items = sampleRanked(10).map((r, i) => ({ ...r, match_percent: i < 5 ? 70 : 40 }));
  search.mockResolvedValue({ ok: true, data: { items, total: 500, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText(/The 5 best matches/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Next/ })).toBeNull();
});

it("says at least 500 when the mood search kept only its best films", async () => {
  const items = sampleRanked(10).map((r) => ({ ...r, match_percent: 40 }));
  search.mockResolvedValue({ ok: true, data: { items, total: 500, total_capped: true, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText("No film matches well · the 3 closest of 500+ films searched")).toBeInTheDocument();
});

it("with the streaming filter, marks films whose streaming is not checked and counts the confirmed ones", async () => {
  const items = sampleRanked(3).map((r, i) => ({
    ...r,
    match_percent: 80,
    movie: {
      ...r.movie,
      availability: {
        in_cinema_de: false,
        streaming_de: i === 0 ? [{ service: "Netflix", type: "subscription", link: "https://x" }] : null,
        subscription_services: i === 0 ? ["Netflix"] : [],
      },
    },
  }));
  search.mockResolvedValue({ ok: true, data: { items, total: 3, hidden_by_exclusion: 0, extended_used: false } });
  const { container } = render(<ResultList criteria={{ ...emptyCriteria(), availability: "stream" }} onOpen={() => {}} />);
  expect(await screen.findByText(/1 of these 3 confirmed on streaming/)).toBeInTheDocument();
  expect(container.querySelectorAll(".result-unchecked")).toHaveLength(2);
});

it("without the streaming filter, no streaming marks", async () => {
  search.mockResolvedValue({ ok: true, data: { items: sampleRanked(3), total: 3, hidden_by_exclusion: 0, extended_used: false } });
  const { container } = render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  await screen.findByText("3 films found");
  expect(container.querySelectorAll(".result-unchecked")).toHaveLength(0);
  expect(screen.queryByText(/confirmed on streaming/)).toBeNull();
});

it("the row below starts higher when there are many strong films", async () => {
  const { moreFloor } = await import("@/components/results/ResultList");
  expect(moreFloor(Array(40).fill(75))).toBe(70);
  expect(moreFloor([...Array(10).fill(75), ...Array(25).fill(62)])).toBe(60);
  expect(moreFloor([...Array(10).fill(65), ...Array(10).fill(55)])).toBe(50);
});

it("counts the good matches, with every film searched after them", async () => {
  const { countText } = await import("@/components/results/ResultList");
  expect(countText(31, false, 70, 20668, false, 8)).toBe("31 good matches from 70% · 20,668 films searched");
  expect(countText(50, true, 60, 500, true, 8)).toBe("50+ good matches from 60% · 500+ films searched");
  expect(countText(3, false, 50, 3, false, 3)).toBe("3 films found"); // all of them match well
  expect(countText(0, false, 50, 50, false, 3)).toBe("No film matches well · the 3 closest of 50 films searched");
});

it("few strong films: the 3 best in front, then weaker ones below, and the explanation says so on demand", async () => {
  const items = sampleRanked(12).map((r, i) => ({ ...r, match_percent: [69, 39, 35, 33, 31, 30, 28, 26, 24, 22, 21, 15][i] }));
  search.mockResolvedValue({ ok: true, data: { items, total: 50, hidden_by_exclusion: 0, extended_used: false } });
  const criteria = { ...emptyCriteria(), person: "Tom Cruise", tags: [{ idx: 1, weight: 8, mode: "prefer" as const }] };
  const { container } = render(<ResultList criteria={criteria} onOpen={() => {}} tagNames={{ 1: "space travel" }} />);
  expect(await screen.findByText(/The 3 best matches/)).toBeInTheDocument();
  expect(container.querySelectorAll(".best .related-card")).toHaveLength(3);
  expect(screen.getByText("8 weaker matches (below 50%)")).toBeInTheDocument(); // down to 20%, the 15% one stays out
  expect(screen.queryByRole("complementary")).toBeNull(); // folded until asked
  await userEvent.click(screen.getByRole("button", { name: /How these results came about/ }));
  const note = screen.getByRole("complementary", { name: "How these results came about" });
  expect(note).toHaveTextContent("Searched for your moods space travel (★★★★), with Tom Cruise.");
  expect(note).toHaveTextContent("the row below goes on with weaker ones");
});

it("a thin search shows one page of weaker films, at most 29, so no « » are needed", async () => {
  const items = sampleRanked(50).map((r, i) => ({ ...r, movie: { ...r.movie, id: `t-${i}` }, match_percent: i === 0 ? 60 : 45 - Math.floor(i / 3) }));
  search.mockResolvedValue({ ok: true, data: { items, total: 200, hidden_by_exclusion: 0, extended_used: false } });
  render(<ResultList criteria={emptyCriteria()} onOpen={() => {}} />);
  expect(await screen.findByText("29 weaker matches (below 50%)")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Next 30" })).toBeNull();
});
