import { expect, it } from "vitest";
import { advance, easeSpeed } from "@/components/home/TileRows";

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
