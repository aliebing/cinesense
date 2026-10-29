import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import FilmTitles from "@/components/home/FilmTitles";
import { mockMatchMedia } from "./fixtures";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

it("alternates titles between an upper and a lower slot", () => {
  mockMatchMedia(() => false);
  render(<FilmTitles titles={["Demo-Film 01", "Demo-Film 02", "Demo-Film 03"]} />);
  act(() => {
    vi.advanceTimersByTime(3700);
  });
  const shown = screen.getAllByTestId("film-title");
  expect(shown).toHaveLength(2);
  expect(shown[0].dataset.slot).not.toBe(shown[1].dataset.slot);
});

it("removes a title after its 6.8 s lifetime", () => {
  mockMatchMedia(() => false);
  render(<FilmTitles titles={["Demo-Film 01", "Demo-Film 02"]} />);
  act(() => {
    vi.advanceTimersByTime(6900);
  });
  expect(screen.queryByText("Demo-Film 01")).toBeNull();
});

it("renders one static title under reduced motion", () => {
  mockMatchMedia((q) => q.includes("prefers-reduced-motion"));
  render(<FilmTitles titles={["Demo-Film 01", "Demo-Film 02"]} />);
  act(() => {
    vi.advanceTimersByTime(8000);
  });
  expect(screen.getAllByTestId("film-title")).toHaveLength(1);
  expect(screen.getByText("Demo-Film 01")).toBeInTheDocument();
});
