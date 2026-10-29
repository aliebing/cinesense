import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import StagePanel from "@/components/genre/StagePanel";
import { emptyCriteria, steer } from "@/lib/searchState";
import { sampleMovies, sampleWorlds } from "./fixtures";

const movie = sampleMovies(1)[0];
const world = sampleWorlds[1];

it("👍 and 👎 send persistent feedback and toggle off", async () => {
  const onFeedback = vi.fn();
  const { rerender } = render(<StagePanel movie={movie} world={world} why="x" feedback={0} onFeedback={onFeedback} onSteer={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: "👍 More like this" }));
  expect(onFeedback).toHaveBeenLastCalledWith(1);
  rerender(<StagePanel movie={movie} world={world} why="x" feedback={1} onFeedback={onFeedback} onSteer={() => {}} />);
  expect(screen.getByRole("button", { name: "👍 More like this" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(screen.getByRole("button", { name: "👍 More like this" }));
  expect(onFeedback).toHaveBeenLastCalledWith(0);
  await userEvent.click(screen.getByRole("button", { name: "👎 Not for me" }));
  expect(onFeedback).toHaveBeenLastCalledWith(-1);
});

it("⚡ and 😂 steer the session", async () => {
  const onSteer = vi.fn();
  render(<StagePanel movie={movie} world={world} why="x" feedback={0} onFeedback={() => {}} onSteer={onSteer} />);
  await userEvent.click(screen.getByRole("button", { name: "⚡ More action" }));
  await userEvent.click(screen.getByRole("button", { name: "😂 Funnier" }));
  expect(onSteer.mock.calls).toEqual([["action"], ["funny"]]);
});

it("steer adds a prefer tag and strengthens it up to 10", () => {
  let c = steer(emptyCriteria(), 5);
  expect(c.tags).toEqual([{ idx: 5, weight: 6, mode: "prefer" }]);
  for (let i = 0; i < 5; i++) c = steer(c, 5);
  expect(c.tags).toEqual([{ idx: 5, weight: 10, mode: "prefer" }]);
  const withNot = { ...emptyCriteria(), tags: [{ idx: 5, weight: 5, mode: "not" as const }] };
  expect(steer(withNot, 5).tags).toEqual([{ idx: 5, weight: 6, mode: "prefer" }]);
});
