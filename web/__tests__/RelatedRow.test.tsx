import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import RelatedRow, { edgeSpeed } from "@/components/genre/RelatedRow";
import { mockMatchMedia, sampleRanked } from "./fixtures";

beforeEach(() => mockMatchMedia(() => false));

it("shows match badges and selects a film on click", async () => {
  const onSelect = vi.fn();
  render(<RelatedRow items={sampleRanked(3)} onSelect={onSelect} />);
  expect(screen.getAllByText("90%").length).toBeGreaterThan(0);
  await userEvent.click(screen.getAllByRole("button", { name: /Demo-Film 02/ })[0]);
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "demo-02" }));
});

it("renders a placeholder for a film without poster", () => {
  const items = sampleRanked(1);
  items[0] = { ...items[0], movie: { ...items[0].movie, poster_url: null } };
  render(<RelatedRow items={items} onSelect={() => {}} />);
  expect(screen.getAllByTestId("image-placeholder").length).toBeGreaterThan(0);
});

it("has no arrow buttons; the mouse steers the row", () => {
  render(<RelatedRow items={sampleRanked(14)} onSelect={() => {}} />);
  expect(screen.queryByRole("button", { name: /Next films|Previous films/ })).toBeNull();
  expect(screen.getByText(/move the mouse left or right/)).toBeInTheDocument();
});

it("edgeSpeed: creeps on in the middle, faster towards the edges, opposite directions, drifts without a pointer", () => {
  expect(edgeSpeed(0.5)).toBeLessThan(0); // middle: keeps going in the current direction …
  expect(Math.abs(edgeSpeed(0.6))).toBeLessThan(20); // … but slowly, so a card can be caught for its trailer
  expect(edgeSpeed(0.5, 1)).toBeGreaterThan(0);
  expect(edgeSpeed(0.9)).toBeLessThan(0); // right: films slide left, new ones come in from the right
  expect(edgeSpeed(0.1)).toBeGreaterThan(0); // left: the other way
  expect(Math.abs(edgeSpeed(1))).toBeGreaterThan(Math.abs(edgeSpeed(0.85)));
  expect(edgeSpeed(1)).toBeCloseTo(-edgeSpeed(0));
  expect(Math.abs(edgeSpeed(1))).toBeGreaterThan(500);
  expect(edgeSpeed(null)).toBeLessThan(0);
  expect(edgeSpeed(null, 1)).toBeGreaterThan(0);
  expect(Math.abs(edgeSpeed(null))).toBeLessThan(60);
});

it("few films: empty boxes fill each loop set, so the row never shows gaps or jumps", async () => {
  const { MIN_SLOTS } = await import("@/components/genre/RelatedRow");
  const { container } = render(<RelatedRow items={sampleRanked(4)} onSelect={() => {}} />);
  const empty = container.querySelectorAll(".related-card--empty");
  expect(empty).toHaveLength(2 * (MIN_SLOTS - 4)); // both copies of the loop
  expect([...empty].every((e) => e.getAttribute("aria-hidden") === "true")).toBe(true);
  expect(screen.getAllByRole("button", { name: /Demo-Film/ }).filter((b) => !b.closest("[aria-hidden]"))).toHaveLength(4);
});

it("enough films: no empty boxes", async () => {
  const { MIN_SLOTS } = await import("@/components/genre/RelatedRow");
  const { container } = render(<RelatedRow items={sampleRanked(MIN_SLOTS)} onSelect={() => {}} />);
  expect(container.querySelectorAll(".related-card--empty")).toHaveLength(0);
});

it("a card that changes width never moves the card under the pointer: the row offset absorbs the shift", async () => {
  const { anchored } = await import("@/components/genre/RelatedRow");
  // the hovered card's layout position moved 160 px left (a wide card before it shrank): the row moves right by 160
  expect(anchored(-500, 900, 740)).toBe(-340);
  expect(anchored(-500, 900, 900)).toBe(-500); // nothing moved
  expect(anchored(-500, null, 740)).toBe(-500); // a new card under the pointer: nothing to compare yet
});
