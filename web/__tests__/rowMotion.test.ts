import { expect, it } from "vitest";
import { advance, easeTowards } from "@/components/home/TileRows";

it("wraps exactly by one loop period in both directions (no jump)", () => {
  expect(advance(-99, -2, 100)).toBeCloseTo(-1);
  expect(advance(-1, 2, 100)).toBeCloseTo(-99);
  expect(advance(-50, -1, 100)).toBeCloseTo(-51);
  expect(advance(-50, -1, 0)).toBeCloseTo(-51); // period unknown yet: just move
});

it("direction comes from the world's place in the full list, so neighbours always alternate", async () => {
  const { rowDirection } = await import("@/components/home/TileRows");
  const order = ["a", "b", "c", "d", "e", "f"];
  expect(rowDirection("f", order, 0)).not.toBe(rowDirection("a", order, 1)); // hero jumps from a to f
  expect(rowDirection("a", order, 0)).not.toBe(rowDirection("b", order, 1));
  expect(rowDirection("x", [], 3)).toBe(1); // unknown world: by slot
});

it("eases towards the target speed instead of jumping", () => {
  const s1 = easeTowards(0, 100, 16, 220);
  expect(s1).toBeGreaterThan(0);
  expect(s1).toBeLessThan(100);
  let s = 0;
  for (let i = 0; i < 200; i++) s = easeTowards(s, 100, 16, 220);
  expect(s).toBeCloseTo(100, 2);
});
