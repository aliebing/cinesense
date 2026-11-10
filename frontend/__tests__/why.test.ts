import { expect, it } from "vitest";
import { stageWhyText } from "@/lib/why";
import { sampleMovies } from "./fixtures";

const movie = { ...sampleMovies(1)[0], ml_rating: 4.21, ml_rating_count: 65056 };

it("uses the search's reasons when the search ranked the film", () => {
  expect(stageWhyText(movie, "Science Fiction", ["space travel 98%"], null)).toBe("Strong on your moods: space travel (98%)");
});

it("without moods says what the film is: one of its world's top-rated films, with the rating", () => {
  expect(stageWhyText(movie, "Science Fiction", [], null)).toBe(
    "One of the top-rated Science Fiction films · MovieLens 4.2/5 from 65,056 ratings",
  );
});

it("with moods says honestly how the film carries them", () => {
  expect(stageWhyText(movie, "Science Fiction", [], [{ tag: "space travel", mode: "prefer", percent: 5 }])).toBe(
    "Not a match for space travel (5%) · One of the top-rated Science Fiction films · MovieLens 4.2/5 from 65,056 ratings",
  );
  const fit = [
    { tag: "dark", mode: "prefer" as const, percent: 78 },
    { tag: "space travel", mode: "must" as const, percent: 12 },
    { tag: "gore", mode: "not" as const, percent: 61 },
  ];
  expect(stageWhyText(movie, "Science Fiction", [], fit)).toBe(
    "Strong on your moods: dark (78%) · hardly space travel (12%) · has what you excluded: gore (61%)",
  );
  expect(stageWhyText(movie, "Science Fiction", [], [{ tag: "space travel", mode: "prefer", percent: 31 }])).toBe(
    "Partly space travel (31%) · One of the top-rated Science Fiction films · MovieLens 4.2/5 from 65,056 ratings",
  );
  expect(stageWhyText(movie, "Science Fiction", [], [{ tag: "dark", mode: "prefer", percent: null }])).toMatch(/^No mood data to compare/);
});
