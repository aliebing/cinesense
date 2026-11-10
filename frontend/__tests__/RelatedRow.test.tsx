import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import RelatedRow, { edgeSpeed, SWEEP_MS, sweepOffset } from "@/components/genre/RelatedRow";
import { mockMatchMedia, sampleRanked } from "./fixtures";

beforeEach(() => mockMatchMedia(() => false));

it("shows match badges and selects a film on click", async () => {
  const onSelect = vi.fn();
  render(<RelatedRow items={sampleRanked(3)} onSelect={onSelect} />);
  expect(screen.getAllByText("90% match").length).toBeGreaterThan(0);
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

it("few films stand still, once each, without empty boxes or the browse hint", async () => {
  const { container } = render(<RelatedRow items={sampleRanked(2)} onSelect={() => {}} />);
  expect(container.querySelectorAll(".related-card")).toHaveLength(2);
  expect(container.querySelector(".related-viewport")).toHaveClass("is-static");
  expect(container.textContent).not.toContain("move the mouse");
});

it("enough films: the row loops (two copies) and invites browsing", async () => {
  const { MIN_SLOTS } = await import("@/components/genre/RelatedRow");
  const { container } = render(<RelatedRow items={sampleRanked(MIN_SLOTS)} onSelect={() => {}} />);
  expect(container.querySelectorAll(".related-card")).toHaveLength(2 * MIN_SLOTS);
  expect(container.textContent).toContain("move the mouse");
});

it("a card that changes width never moves the card under the pointer: the row offset absorbs the shift", async () => {
  const { anchored } = await import("@/components/genre/RelatedRow");
  // the hovered card's layout position moved 160 px left (a wide card before it shrank): the row moves right by 160
  expect(anchored(-500, 900, 740)).toBe(-340);
  expect(anchored(-500, 900, 900)).toBe(-500); // nothing moved
  expect(anchored(-500, null, 740)).toBe(-500); // a new card under the pointer: nothing to compare yet
});

it("holds still while the visitor types in the chat drawer", async () => {
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
  const { container } = render(<RelatedRow items={sampleRanked(14)} onSelect={() => {}} drift />);
  const track = container.querySelector(".related-track") as HTMLElement;
  let t = 0;
  const run = (n: number) => {
    for (let i = 0; i < n; i++) frames.shift()?.((t += 16));
  };
  run(30);
  noteTyping();
  run(1);
  const held = track.style.transform;
  run(30);
  expect(track.style.transform).toBe(held);
  stopTyping();
  run(30);
  expect(track.style.transform).not.toBe(held);
  vi.restoreAllMocks();
});

it("a running row that shrinks to a few films stands still at the start, not where the loop had slid to", () => {
  const { container, rerender } = render(<RelatedRow items={sampleRanked(14)} onSelect={() => {}} />);
  const track = container.querySelector<HTMLElement>(".related-track")!;
  track.style.transform = "translate3d(-4000px, 0, 0)"; // where the running loop had got to
  rerender(<RelatedRow items={sampleRanked(4)} onSelect={() => {}} />);
  expect(container.querySelector<HTMLElement>(".related-track")!.style.transform).toBe("");
});

/** Lays the row out as a browser would: the viewport is `viewport` px wide, every card `card` px. */
function layout(viewport: number, card: number) {
  const restore: (() => void)[] = [];
  const stub = (prop: "clientWidth" | "offsetWidth", get: (el: HTMLElement) => number) => {
    const before = Object.getOwnPropertyDescriptor(HTMLElement.prototype, prop);
    Object.defineProperty(HTMLElement.prototype, prop, { configurable: true, get() { return get(this); } });
    restore.push(() => before && Object.defineProperty(HTMLElement.prototype, prop, before));
  };
  stub("clientWidth", (el) => (el.classList.contains("related-viewport") ? viewport : 0));
  stub("offsetWidth", (el) => (el.classList.contains("related-wrap") || el.classList.contains("related-card") ? card : 0));
  vi.stubGlobal("ResizeObserver", class {
    constructor(private cb: () => void) {}
    observe() { this.cb(); }
    disconnect() {}
  });
  return () => { restore.forEach((r) => r()); vi.unstubAllGlobals(); };
}

it("many films that all fit in the visible width stand still", async () => {
  const undo = layout(5000, 100);
  const { container } = render(<RelatedRow items={sampleRanked(20)} onSelect={() => {}} />);
  expect(container.querySelector(".related-viewport")).toHaveClass("is-static");
  expect(container.querySelectorAll(".related-card")).toHaveLength(20);
  expect(container.textContent).not.toContain("move the mouse");
  undo();
});

it("a few films that do not fit in the visible width run as a loop", async () => {
  const undo = layout(300, 100);
  const { container } = render(<RelatedRow items={sampleRanked(6)} onSelect={() => {}} />);
  expect(container.querySelector(".related-viewport")).not.toHaveClass("is-static");
  expect(container.querySelectorAll(".related-card")).toHaveLength(12);
  undo();
});

it("edgeSpeed without drift: still unless the mouse steers towards an edge", () => {
  expect(edgeSpeed(null, -1, false)).toBe(0); // no pointer: the best matches stay where they are
  expect(edgeSpeed(0.5, -1, false)).toBe(0); // middle: no creeping either
  expect(edgeSpeed(0.95, -1, false)).toBeLessThan(0); // the edges still browse
  expect(edgeSpeed(0.05, -1, false)).toBeGreaterThan(0);
});

it("a card widened by its trailer does not make a fitting row start looping", async () => {
  const undo = layout(900, 100);
  const wide = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth")!;
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
    configurable: true,
    get() {
      const base = wide.get!.call(this) as number;
      return this === this.parentElement?.firstElementChild && base ? 300 : base; // the first card plays its trailer
    },
  });
  const { container } = render(<RelatedRow items={sampleRanked(8)} onSelect={() => {}} />);
  expect(container.querySelector(".related-viewport")).toHaveClass("is-static");
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", wide);
  undo();
});

it("sweeps from start to target, slow at both ends and fast in between", () => {
  expect(sweepOffset(0, -10000, 0)).toBe(0);
  expect(sweepOffset(0, -10000, SWEEP_MS)).toBe(-10000);
  expect(sweepOffset(0, -10000, SWEEP_MS * 2)).toBe(-10000); // never past the target
  expect(sweepOffset(0, -10000, SWEEP_MS / 2)).toBeCloseTo(-5000);
  const early = -sweepOffset(0, -10000, SWEEP_MS * 0.1);
  const middle = -sweepOffset(0, -10000, SWEEP_MS * 0.55) + sweepOffset(0, -10000, SWEEP_MS * 0.45);
  expect(early).toBeLessThan(middle / 5); // the first tenth covers far less than a tenth around the middle
  expect(sweepOffset(-8000, 0, SWEEP_MS)).toBe(0); // backwards too
});
