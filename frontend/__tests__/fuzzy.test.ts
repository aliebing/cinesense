import { expect, it } from "vitest";
import { fuzzyFind } from "@/lib/fuzzy";

const tags = ["medieval", "space travel", "dark", "dark comedy", "travel", "time travel", "horror"];

it("substring hits come first, those starting with the input before the rest", () => {
  expect(fuzzyFind("dar", tags)).toEqual(["dark", "dark comedy"]);
  expect(fuzzyFind("travel", tags)).toEqual(["travel", "space travel", "time travel"]);
});

it("tolerates typos in the whole tag or in one of its words", () => {
  expect(fuzzyFind("medival", tags)).toEqual(["medieval"]);
  expect(fuzzyFind("horor", tags)).toEqual(["horror"]);
  expect(fuzzyFind("spcae", tags)).toContain("space travel");
});

it("ignores case and accents, and finds nothing for unrelated input", () => {
  expect(fuzzyFind("MÉDIEVAL", tags)).toEqual(["medieval"]);
  expect(fuzzyFind("zzzz", tags)).toEqual([]);
  expect(fuzzyFind("", tags)).toEqual([]);
});
