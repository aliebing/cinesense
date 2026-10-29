import { render, screen, waitFor } from "@testing-library/react";
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
};
vi.mock("@/lib/api", () => ({
  getWorlds: () => api.getWorlds(),
  getWorldMovies: (id: string) => api.getWorldMovies(id),
  getMovie: (id: string) => api.getMovie(id),
  getRelated: (id: string, worldId?: string) => api.getRelated(id, worldId),
  discover: (...a: unknown[]) => api.discover(...a),
  getTags: () => Promise.resolve({ ok: true, data: [{ idx: 0, tag: "dark" }] }),
}));

import GenreView from "@/components/genre/GenreView";

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset());
  notFound.mockClear();
  mockMatchMedia(() => false);
  api.getWorlds.mockResolvedValue({ ok: true, data: sampleWorlds });
  api.getWorldMovies.mockResolvedValue({ ok: true, data: sampleRanked(4) });
  api.getRelated.mockResolvedValue({ ok: true, data: sampleRanked(4).slice(1) });
});

it("puts the requested film on stage", async () => {
  api.getMovie.mockResolvedValue({ ok: true, data: sampleMovies(3)[2] });
  render(<GenreView worldId="action" filmId="demo-03" />);
  expect(await screen.findByRole("heading", { name: "Demo-Film 03" })).toBeInTheDocument();
  expect(screen.getByText("World: Action & Adrenaline")).toBeInTheDocument();
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
