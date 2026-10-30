import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";
import TileRows, { visibleWorlds } from "@/components/home/TileRows";
import { mockMatchMedia, sampleMovies, sampleWorlds } from "./fixtures";

beforeEach(() => mockMatchMedia(() => false));

const rows = [
  { world: sampleWorlds[0], movies: sampleMovies(6) },
  { world: sampleWorlds[1], movies: sampleMovies(6) },
];

it("renders one decorative row per world: no label, no buttons, no trailers", () => {
  render(<TileRows rows={rows} variedSpeed={false} />);
  expect(screen.getAllByTestId("tile-row")).toHaveLength(2);
  expect(screen.queryByRole("link", { name: "Suspense & Mystery" })).toBeNull();
  expect(document.querySelectorAll(".tile-rows button")).toHaveLength(0);
  expect(screen.queryByTestId("hover-trailer")).toBeNull();
});

it("uses the title-art poster and falls back to a title card", () => {
  const withArt = sampleMovies(1)[0];
  const noArt = { ...sampleMovies(2)[1], horizontal_poster_url: null, backdrop_url: null, poster_url: null };
  render(<TileRows rows={[{ world: sampleWorlds[0], movies: [withArt, noArt] }]} variedSpeed={false} />);
  expect(document.querySelector(`img[src="${withArt.horizontal_poster_url}"]`)).not.toBeNull();
  expect(screen.getAllByTestId("title-card")[0]).toHaveTextContent("Demo-Film 02");
});

it("visibleWorlds wraps around from the active world", () => {
  const ws = ["a", "b", "c", "d", "e", "f"].map((id) => ({ ...sampleWorlds[0], id }));
  expect(visibleWorlds(4, ws).map((w) => w.id)).toEqual(["e", "f", "a", "b"]);
});
