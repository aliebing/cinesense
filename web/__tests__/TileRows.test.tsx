import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import TileRows from "@/components/home/TileRows";
import { mockMatchMedia, sampleMovies } from "./fixtures";

beforeEach(() => mockMatchMedia(() => false));

it("renders four rows of buttons labelled by film title and calls onSelect", async () => {
  const onSelect = vi.fn();
  render(<TileRows movies={sampleMovies(12)} rows={4} onSelect={onSelect} variedSpeed={false} />);
  expect(screen.getAllByTestId("tile-row")).toHaveLength(4);
  await userEvent.click(screen.getAllByRole("button", { name: "Demo-Film 01" })[0]);
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "demo-01" }));
});

it("shows placeholder card when poster is missing", () => {
  const movie = { ...sampleMovies(1)[0], poster_url: null, backdrop_url: null, horizontal_poster_url: null };
  render(<TileRows movies={[movie]} rows={1} onSelect={() => {}} variedSpeed={false} />);
  expect(screen.getAllByTestId("image-placeholder").length).toBeGreaterThan(0);
});
