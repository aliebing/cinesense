import { expect, it } from "vitest";
import { advance, easeSpeed, easeTowards } from "@/components/home/TileRows";

it("wraps exactly by one loop period in both directions (no jump)", () => {
  expect(advance(-99, -2, 100)).toBeCloseTo(-1);
  expect(advance(-1, 2, 100)).toBeCloseTo(-99);
  expect(advance(-50, -1, 100)).toBeCloseTo(-51);
  expect(advance(-50, -1, 0)).toBeCloseTo(-51); // period unknown yet: just move
});

it("eases towards the target speed instead of stopping abruptly", () => {
  const s1 = easeSpeed(1, 0.3, 16);
  expect(s1).toBeLessThan(1);
  expect(s1).toBeGreaterThan(0.3);
  let s = 1;
  for (let i = 0; i < 200; i++) s = easeSpeed(s, 0.3, 16);
  expect(s).toBeCloseTo(0.3, 2);
});

it("direction comes from the world's place in the full list, so neighbours always alternate", async () => {
  const { rowDirection } = await import("@/components/home/TileRows");
  const order = ["a", "b", "c", "d", "e", "f"];
  expect(rowDirection("f", order, 0)).not.toBe(rowDirection("a", order, 1)); // hero jumps from a to f
  expect(rowDirection("a", order, 0)).not.toBe(rowDirection("b", order, 1));
  expect(rowDirection("x", [], 3)).toBe(1); // unknown world: by slot
});

it("during a search the short list runs right and the rows around it left", async () => {
  const { searchAwareDirection } = await import("@/components/home/TileRows");
  const order = ["a", "b", "c"];
  expect(searchAwareDirection("search-hits", true, true, order, 1)).toBe(1);
  expect(searchAwareDirection("a", false, true, order, 0)).toBe(-1);
  expect(searchAwareDirection("b", false, true, order, 2)).toBe(-1);
  expect(searchAwareDirection("b", false, false, order, 1)).toBe(1); // no search: worlds alternate as before
});

it("the target speed: full, slower while pointing, a crawl while a trailer plays", async () => {
  const { targetFactor } = await import("@/components/home/TileRows");
  expect(targetFactor(false, false)).toBe(1);
  expect(targetFactor(true, false)).toBeLessThan(0.6);
  expect(targetFactor(true, true)).toBeLessThan(0.1);
  expect(targetFactor(false, true)).toBeGreaterThan(0); // never a hard stop
});

it("easeTowards approaches any target smoothly (used by the related row)", () => {
  const s1 = easeTowards(0, 100, 16, 220);
  expect(s1).toBeGreaterThan(0);
  expect(s1).toBeLessThan(100);
  let s = 0;
  for (let i = 0; i < 200; i++) s = easeTowards(s, 100, 16, 220);
  expect(s).toBeCloseTo(100, 2);
});
