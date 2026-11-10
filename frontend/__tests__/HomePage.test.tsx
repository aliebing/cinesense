import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { emptyCriteria, setSearchState } from "@/lib/searchState";
import { mockMatchMedia, sampleHome, sampleRanked } from "./fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const getHome = vi.fn();
const discover = vi.fn();
const search = vi.fn();
vi.mock("@/lib/api", () => ({
  getHome: () => getHome(),
  getTags: () => Promise.resolve({ ok: true, data: [] }),
  getProfile: () => Promise.resolve({ ok: true, data: { liked: [], disliked: [], taste: [] } }),
  discover: (...a: unknown[]) => discover(...a),
  search: (...a: unknown[]) => search(...a),
}));

import HomePage from "@/components/home/HomePage";

beforeEach(() => {
  push.mockReset();
  getHome.mockReset();
  discover.mockReset();
  search.mockReset();
  setSearchState(emptyCriteria());
  mockMatchMedia(() => false);
});

it("shows the claim and navigates to the genre page when a tile is clicked", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  expect(screen.getByText("Don't choose a movie.")).toBeInTheDocument();
  expect(screen.getByText("Choose a feeling.")).toBeInTheDocument();
  const tile = await screen.findAllByRole("button", { name: "Demo-Film 02" });
  await userEvent.click(tile[0]);
  expect(push).toHaveBeenCalledWith("/world/suspense?film=demo-02");
});

it("a search (chat or chips) takes over the rows: its hits first, then the worlds they belong to", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  discover.mockResolvedValue({ ok: true, data: { items: sampleRanked(6), total: 6, hidden_by_exclusion: 0, extended_used: false } });
  setSearchState({ ...emptyCriteria(), tags: [{ idx: 7, weight: 8, mode: "prefer" }] });
  render(<HomePage />);
  await waitFor(() => expect(document.querySelector('.tile-row-wrap[data-world="search-hits"]')).not.toBeNull());
  const worlds = [...document.querySelectorAll(".tile-row-wrap")].map((r) => r.getAttribute("data-world"));
  expect(worlds[0]).toBe("search-hits");
  expect(discover).toHaveBeenCalledWith(expect.objectContaining({ world_id: null }), 0, expect.any(Number));
});

it("shows a loading bar while a search loads its rows, and dims the rows meanwhile", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  let answer: (v: unknown) => void = () => {};
  const hits = { ok: true, data: { items: sampleRanked(6), total: 6, hidden_by_exclusion: 0, extended_used: false } };
  discover.mockResolvedValue(hits); // the world rows after the hits
  discover.mockImplementationOnce(() => new Promise((r) => (answer = r))); // the hits wait
  setSearchState({ ...emptyCriteria(), tags: [{ idx: 7, weight: 8, mode: "prefer" }] });
  render(<HomePage />);
  expect(await screen.findByRole("progressbar", { name: "Loading results" })).toBeInTheDocument();
  expect(document.querySelector(".home-rows")).toHaveClass("is-busy");
  await waitFor(() => expect(discover).toHaveBeenCalled());
  await act(async () => answer(hits));
  await waitFor(() => expect(screen.queryByRole("progressbar")).toBeNull());
  expect(document.querySelector(".home-rows")).not.toHaveClass("is-busy");
});

it("shows the mood settings panel even before any tag is set", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  expect(screen.getByRole("heading", { name: "Your mood settings" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "+ Tag" })).toBeInTheDocument();
});

it("keeps claim and chat when the backend is unreachable", async () => {
  getHome.mockResolvedValue({ ok: false, error: "network" });
  render(<HomePage />);
  await waitFor(() => expect(screen.getByText("Couldn't load films")).toBeInTheDocument());
  expect(screen.getByText("Don't choose a movie.")).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "Message CineSense" })).toBeInTheDocument();
});

it("shows one tile strip and no film titles on narrow screens", async () => {
  mockMatchMedia((q) => q.includes("max-width: 759px"));
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  await screen.findAllByTestId("tile-row");
  expect(screen.getAllByTestId("tile-row")).toHaveLength(1);
  expect(screen.queryByTestId("film-titles")).toBeNull();
});

it("shows English quick filters without a language chip", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  const { container } = render(<HomePage />);
  const chips = [...container.querySelectorAll(".chat-chips button")].map((c) => c.textContent);
  expect(chips).toEqual(["🎬 In cinemas", "📺 Streaming", "🚫 No horror"]);
  expect(screen.queryByText(/Englisch|English/)).toBeNull();
});

it("shows the films of the mood on screen in two rows running against each other, and follows the hero after 12 s", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  await screen.findAllByTestId("tile-row");
  const rowIds = () => [...document.querySelectorAll(".tile-row-wrap")].map((r) => r.getAttribute("data-world"));
  expect(rowIds()).toEqual(["mood-0", "mood-1"]);
  expect(screen.getAllByRole("button", { name: "Demo-Film 02" }).length).toBeGreaterThan(0); // suspense
  expect(screen.queryAllByRole("button", { name: "Demo-Film 01" })).toHaveLength(0); // action: not on show yet
  await act(async () => {
    await vi.advanceTimersByTimeAsync(12100);
  });
  expect(rowIds()).toEqual(["mood-0", "mood-1"]); // the same rows run on, only their films change
  expect(screen.getAllByRole("button", { name: "Demo-Film 01" }).length).toBeGreaterThan(0);
  expect(screen.queryAllByRole("button", { name: "Demo-Film 02" })).toHaveLength(0);
  vi.useRealTimers();
});

it("nav shortcuts open the results pre-filtered and 👤 opens the profile", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  const nav = screen.getByRole("navigation", { name: "Main navigation" });
  await userEvent.click(within(nav).getByRole("button", { name: "📺 Streaming" }));
  expect(push).toHaveBeenCalledWith("/results");
  expect(JSON.parse(window.sessionStorage.getItem("cinesense.search") ?? "{}").availability).toBe("stream");
  await userEvent.click(within(nav).getByRole("button", { name: "Profile" }));
  expect(await screen.findByRole("dialog", { name: "Your profile" })).toBeInTheDocument();
});

it("Show results opens the search overview", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  discover.mockResolvedValue({ ok: true, data: { items: sampleRanked(3), total: 3, hidden_by_exclusion: 0, extended_used: false } });
  setSearchState({ ...emptyCriteria(), tags: [{ idx: 7, weight: 8, mode: "prefer" }] });
  render(<HomePage />);
  await userEvent.click(await screen.findByRole("button", { name: "Show results →" }));
  expect(push).toHaveBeenCalledWith("/results");
});

it("shows where you are: the home page in the breadcrumb", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByText("Home")).toHaveAttribute("aria-current", "page");
});

it("uses the rows the server already fetched and does not ask again", async () => {
  render(<HomePage initial={sampleHome} />);
  expect(screen.getAllByRole("button", { name: "Demo-Film 02" }).length).toBeGreaterThan(0); // at once, no waiting
  await act(async () => {});
  expect(getHome).not.toHaveBeenCalled();
});

it("loads only the hero pictures on show, fading out and next", () => {
  const film = sampleHome.rows.action[0];
  const worlds = Array.from({ length: 6 }, (_, i) => ({ ...sampleHome.worlds[0], id: `w${i}` }));
  const rows = Object.fromEntries(worlds.map((w, i) => [w.id, [{ ...film, id: `f${i}`, backdrop_url: `b${i}.jpg` }]]));
  const { container } = render(<HomePage initial={{ ...sampleHome, worlds, rows }} />);
  const loaded = [...container.querySelectorAll<HTMLElement>(".hero-img")].map((el) => el.style.backgroundImage);
  expect(loaded).toHaveLength(6);
  expect(loaded.filter(Boolean)).toEqual(['url("b0.jpg")', 'url("b1.jpg")', 'url("b5.jpg")']); // on show, next, previous
});
