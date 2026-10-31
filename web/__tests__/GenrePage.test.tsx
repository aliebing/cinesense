import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { mockMatchMedia, sampleMovies, sampleRanked, sampleWorlds } from "./fixtures";

// The real notFound() throws to reach the not-found boundary; the mock only records the call.
const notFound = vi.fn();
const replace = vi.fn();
vi.mock("next/navigation", () => ({ notFound: () => notFound(), useRouter: () => ({ replace, push: vi.fn() }) }));

const api = {
  getWorlds: vi.fn(),
  getWorldMovies: vi.fn(),
  getMovie: vi.fn(),
  getRelated: vi.fn(),
  discover: vi.fn(),
  search: vi.fn(),
  getProfile: vi.fn(),
  sendFeedback: vi.fn(),
};
vi.mock("@/lib/api", () => ({
  getWorlds: () => api.getWorlds(),
  getWorldMovies: (id: string) => api.getWorldMovies(id),
  getMovie: (id: string) => api.getMovie(id),
  getRelated: (id: string, worldId?: string) => api.getRelated(id, worldId),
  discover: (...a: unknown[]) => api.discover(...a),
  search: (...a: unknown[]) => api.search(...a),
  getTags: () => Promise.resolve({ ok: true, data: [{ idx: 0, tag: "dark" }, { idx: 3, tag: "action" }] }),
  getProfile: () => api.getProfile(),
  sendFeedback: (...a: unknown[]) => api.sendFeedback(...a),
}));

import GenreView from "@/components/genre/GenreView";

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  notFound.mockClear();
  mockMatchMedia(() => false);
  api.getWorlds.mockResolvedValue({ ok: true, data: sampleWorlds });
  api.getWorldMovies.mockResolvedValue({ ok: true, data: sampleRanked(4) });
  api.getRelated.mockResolvedValue({ ok: true, data: sampleRanked(4).slice(1) });
  api.getProfile.mockResolvedValue({ ok: true, data: { liked: [], disliked: [], taste: [] } });
  api.sendFeedback.mockResolvedValue({ ok: true, data: { liked: [{ id: "demo-03", title: "x", year: null }], disliked: [], taste: [] } });
});

it("puts the requested film on stage", async () => {
  api.getMovie.mockResolvedValue({ ok: true, data: sampleMovies(3)[2] });
  render(<GenreView worldId="action" filmId="demo-03" />);
  expect(await screen.findByRole("heading", { name: "Demo-Film 03" })).toBeInTheDocument();
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByRole("link", { name: "Action & Adrenaline" })).toHaveAttribute("href", "/world/action");
  expect(within(crumbs).getByText("Demo-Film 03")).toHaveAttribute("aria-current", "page");
});

it("falls back to the top-ranked film without a film param", async () => {
  render(<GenreView worldId="action" filmId={null} />);
  expect(await screen.findByRole("heading", { name: "Demo-Film 01" })).toBeInTheDocument();
  expect(api.getMovie).not.toHaveBeenCalled();
});

it("calls notFound for an unknown film", async () => {
  api.getMovie.mockResolvedValue({ ok: false, error: "not_found" });
  render(<GenreView worldId="action" filmId="nope" />);
  await waitFor(() => expect(notFound).toHaveBeenCalled());
});

it("calls notFound for an unknown world", async () => {
  api.getWorldMovies.mockResolvedValue({ ok: false, error: "not_found" });
  render(<GenreView worldId="horror" filmId={null} />);
  await waitFor(() => expect(notFound).toHaveBeenCalled());
});

it("shows an error state when the backend is unreachable", async () => {
  api.getWorlds.mockResolvedValue({ ok: false, error: "network" });
  api.getWorldMovies.mockResolvedValue({ ok: false, error: "network" });
  render(<GenreView worldId="action" filmId={null} />);
  expect(await screen.findByText("Couldn't load films")).toBeInTheDocument();
});

it("asks for related films within the world shown on the page", async () => {
  render(<GenreView worldId="action" filmId={null} />);
  await screen.findByRole("heading", { name: "Demo-Film 01" });
  await waitFor(() => expect(api.getRelated).toHaveBeenCalledWith("demo-01", "action"));
});

it("re-ranks the related row with the chip criteria inside the world", async () => {
  const { setSearchState, emptyCriteria } = await import("@/lib/searchState");
  setSearchState({ ...emptyCriteria(), tags: [{ idx: 0, weight: 6, mode: "prefer" }] });
  api.discover.mockResolvedValue({ ok: true, data: { items: sampleRanked(3), total: 3, hidden_by_exclusion: 0, extended_used: false } });
  render(<GenreView worldId="action" filmId={null} />);
  await screen.findByRole("heading", { name: "Demo-Film 01" });
  await waitFor(() => expect(api.discover).toHaveBeenCalled());
  expect(api.discover.mock.calls[0][0]).toMatchObject({ world_id: "action", tags: [{ idx: 0, weight: 6, mode: "prefer" }] });
  setSearchState(emptyCriteria());
});

it("👍 stores feedback, marks the button and re-ranks the row", async () => {
  const userEvent = (await import("@testing-library/user-event")).default;
  api.getMovie.mockResolvedValue({ ok: true, data: sampleMovies(3)[2] });
  render(<GenreView worldId="action" filmId="demo-03" />);
  const like = await screen.findByRole("button", { name: "👍 More like this" });
  await waitFor(() => expect(api.getRelated).toHaveBeenCalledTimes(1));
  await userEvent.click(like);
  expect(api.sendFeedback).toHaveBeenCalledWith("demo-03", 1);
  await waitFor(() => expect(screen.getByRole("button", { name: "👍 More like this" })).toHaveAttribute("aria-pressed", "true"));
  await waitFor(() => expect(api.getRelated).toHaveBeenCalledTimes(2));
});

it("⚡ adds the action tag to the session's chips", async () => {
  const userEvent = (await import("@testing-library/user-event")).default;
  const { emptyCriteria, setSearchState } = await import("@/lib/searchState");
  setSearchState(emptyCriteria());
  api.getMovie.mockResolvedValue({ ok: true, data: sampleMovies(3)[2] });
  api.discover.mockResolvedValue({ ok: true, data: { items: sampleRanked(2), total: 2, hidden_by_exclusion: 0, extended_used: false } });
  render(<GenreView worldId="action" filmId="demo-03" />);
  await userEvent.click(await screen.findByRole("button", { name: "⚡ More action" }));
  await waitFor(() => expect(api.discover).toHaveBeenCalled());
  expect(api.discover.mock.calls[0][0].tags).toEqual([{ idx: 3, weight: 6, mode: "prefer" }]);
});

it("a quick double click on 👍 sends one request", async () => {
  const userEvent = (await import("@testing-library/user-event")).default;
  api.getMovie.mockResolvedValue({ ok: true, data: sampleMovies(3)[2] });
  let resolve: (v: unknown) => void = () => {};
  api.sendFeedback.mockImplementation(() => new Promise((r) => (resolve = r)));
  render(<GenreView worldId="action" filmId="demo-03" />);
  const like = await screen.findByRole("button", { name: "👍 More like this" });
  await userEvent.click(like);
  await userEvent.click(like);
  expect(api.sendFeedback).toHaveBeenCalledTimes(1);
  resolve({ ok: true, data: { liked: [], disliked: [], taste: [] } });
});

it("opened from the search, the row holds the other matches of the whole search with their reasons", async () => {
  const { setSearchState, emptyCriteria } = await import("@/lib/searchState");
  setSearchState({ ...emptyCriteria(), person: "Gérard Depardieu" });
  const items = sampleRanked(3).map((r) => ({ ...r, reasons: ["with Gérard Depardieu"] }));
  api.getMovie.mockResolvedValue({ ok: true, data: items[0].movie });
  api.search.mockResolvedValue({ ok: true, data: { items, total: 3, hidden_by_exclusion: 0, extended_used: false } });
  render(<GenreView worldId="action" filmId={items[0].movie.id} fromSearch />);
  expect(await screen.findByRole("region", { name: "Your other matches" })).toBeInTheDocument();
  expect(api.search.mock.calls[0][0]).toMatchObject({ person: "Gérard Depardieu" });
  expect(api.discover).not.toHaveBeenCalled();
  expect(screen.getByText("with Gérard Depardieu", { selector: ".stage-why span" })).toBeInTheDocument();
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByRole("link", { name: "Search" })).toHaveAttribute("href", "/results"); // back to the overview
  setSearchState(emptyCriteria());
});
