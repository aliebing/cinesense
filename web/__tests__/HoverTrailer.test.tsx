import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import HoverTrailer from "@/components/media/HoverTrailer";
import { resetActiveTrailer } from "@/lib/useActiveTrailer";
import type { Movie } from "@/lib/types";
import { mockMatchMedia, sampleMovies } from "./fixtures";

const [a, b]: Movie[] = sampleMovies(2).map((m, i) => ({ ...m, youtube_key: i === 0 ? "keyA" : "keyB" }));

beforeEach(() => {
  vi.useFakeTimers();
  resetActiveTrailer();
  mockMatchMedia(() => false);
});
afterEach(() => vi.useRealTimers());

function tile(movie = a) {
  return (
    <HoverTrailer movie={movie}>
      <span>{movie.title}</span>
    </HoverTrailer>
  );
}

it("starts muted after the 500 ms intent delay", () => {
  render(tile());
  fireEvent.pointerEnter(screen.getByTestId("hover-trailer"));
  act(() => vi.advanceTimersByTime(400));
  expect(document.querySelector("iframe")).toBeNull();
  act(() => vi.advanceTimersByTime(150));
  const src = document.querySelector("iframe")!.getAttribute("src")!;
  expect(src).toContain("youtube-nocookie.com/embed/keyA");
  expect(src).toContain("mute=1");
});

it("unloads the iframe on leave", () => {
  render(tile());
  const el = screen.getByTestId("hover-trailer");
  fireEvent.pointerEnter(el);
  act(() => vi.advanceTimersByTime(600));
  fireEvent.pointerLeave(el);
  expect(document.querySelector("iframe")).toBeNull();
});

it("plays only one trailer at a time", () => {
  render(
    <>
      {tile(a)}
      {tile(b)}
    </>,
  );
  const [ta, tb] = screen.getAllByTestId("hover-trailer");
  fireEvent.pointerEnter(ta);
  act(() => vi.advanceTimersByTime(600));
  fireEvent.pointerEnter(tb);
  act(() => vi.advanceTimersByTime(600));
  const frames = document.querySelectorAll("iframe");
  expect(frames).toHaveLength(1);
  expect(frames[0].getAttribute("src")).toContain("keyB");
});

it("unmute button switches the src to mute=0", () => {
  render(tile());
  fireEvent.pointerEnter(screen.getByTestId("hover-trailer"));
  act(() => vi.advanceTimersByTime(600));
  fireEvent.click(screen.getByRole("button", { name: "Unmute trailer" }));
  expect(document.querySelector("iframe")!.getAttribute("src")).toContain("mute=0");
  expect(screen.getByRole("button", { name: "Mute trailer" })).toBeInTheDocument();
});

it("shows a note and no iframe without a trailer", () => {
  render(tile({ ...a, youtube_key: null }));
  fireEvent.pointerEnter(screen.getByTestId("hover-trailer"));
  act(() => vi.advanceTimersByTime(600));
  expect(document.querySelector("iframe")).toBeNull();
  expect(screen.getByText("No trailer available")).toBeInTheDocument();
});

it("under reduced motion requires a click", () => {
  mockMatchMedia((q) => q.includes("prefers-reduced-motion"));
  render(tile());
  fireEvent.pointerEnter(screen.getByTestId("hover-trailer"));
  act(() => vi.advanceTimersByTime(600));
  expect(document.querySelector("iframe")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Play trailer" }));
  expect(document.querySelector("iframe")).not.toBeNull();
});
