import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import TileRows, { visibleWorlds } from "@/components/home/TileRows";
import { mockMatchMedia, sampleMovies, sampleWorlds } from "./fixtures";

beforeEach(() => mockMatchMedia(() => false));

const rows = [
  { world: sampleWorlds[0], movies: sampleMovies(6) },
  { world: sampleWorlds[1], movies: sampleMovies(6) },
];

it("renders one row per world without a category label and calls onSelect", async () => {
  const onSelect = vi.fn();
  render(<TileRows rows={rows} onSelect={onSelect} />);
  expect(screen.getAllByTestId("tile-row")).toHaveLength(2);
  expect(screen.queryByRole("link", { name: "Suspense & Mystery" })).toBeNull();
  await userEvent.click(screen.getAllByRole("button", { name: "Demo-Film 01" })[0]);
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "demo-01" }));
});

it("uses the title-art poster and falls back to a title card", () => {
  const withArt = sampleMovies(1)[0];
  const noArt = { ...sampleMovies(2)[1], horizontal_poster_url: null, backdrop_url: null, poster_url: null };
  render(<TileRows rows={[{ world: sampleWorlds[0], movies: [withArt, noArt] }]} onSelect={() => {}} />);
  expect(document.querySelector(`img[src="${withArt.horizontal_poster_url}"]`)).not.toBeNull();
  expect(screen.getAllByTestId("title-card")[0]).toHaveTextContent("Demo-Film 02");
});

it("visibleWorlds wraps around from the active world", () => {
  const ws = ["a", "b", "c", "d", "e", "f"].map((id) => ({ ...sampleWorlds[0], id }));
  expect(visibleWorlds(4, ws).map((w) => w.id)).toEqual(["e", "f", "a", "b"]);
});

it("never starts a trailer on the home tiles, however long the pointer rests", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const movies = sampleMovies(2).map((m) => ({ ...m, youtube_key: "abc123" }));
  render(<TileRows rows={[{ world: sampleWorlds[0], movies }]} onSelect={() => {}} />);
  await userEvent.hover(screen.getAllByRole("button", { name: "Demo-Film 01" })[0]);
  await vi.advanceTimersByTimeAsync(2000);
  expect(screen.queryByTestId("hover-trailer")).toBeNull();
  expect(document.querySelector("iframe")).toBeNull();
  vi.useRealTimers();
});

it("measures each row's loop length once, not on every frame (a layout read per frame made typing lag)", () => {
  const frames: FrameRequestCallback[] = [];
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
    frames.push(cb);
    return frames.length;
  });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
  const reads = vi
    .spyOn(HTMLElement.prototype, "offsetLeft", "get")
    .mockImplementation(function (this: HTMLElement) {
      return Array.from(this.parentElement?.children ?? []).indexOf(this) * 100;
    });
  render(<TileRows rows={rows} onSelect={() => {}} />);
  const run = (n: number) => {
    for (let i = 0; i < n; i++) frames.shift()?.(performance.now() + i * 16);
  };
  run(2);
  const afterFirst = reads.mock.calls.length;
  run(30);
  expect(reads.mock.calls.length).toBe(afterFirst);
  vi.restoreAllMocks();
});

it("stands still at once while the visitor types in the chat and moves again afterwards", async () => {
  const { noteTyping, stopTyping } = await import("@/lib/typingPause");
  const frames: FrameRequestCallback[] = [];
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
    frames.push(cb);
    return frames.length;
  });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
  vi.spyOn(HTMLElement.prototype, "offsetLeft", "get").mockImplementation(function (this: HTMLElement) {
    return Array.from(this.parentElement?.children ?? []).indexOf(this) * 100;
  });
  render(<TileRows rows={rows} onSelect={() => {}} />);
  let t = 0;
  const run = (n: number) => {
    for (let i = 0; i < n; i++) frames.shift()?.((t += 16));
  };
  const row = screen.getAllByTestId("tile-row")[0];
  run(5);
  noteTyping();
  run(1);
  const held = row.style.transform;
  run(20);
  expect(row.style.transform).toBe(held);
  stopTyping();
  run(20);
  expect(row.style.transform).not.toBe(held);
  vi.restoreAllMocks();
});
