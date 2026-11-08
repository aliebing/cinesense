import { expect, test } from "vitest";
import { filterChips } from "@/components/search/SearchChips";
import { emptyCriteria } from "@/lib/searchState";

test("the streaming chip names the wished-for services and clears them too", () => {
  const chip = filterChips({ ...emptyCriteria(), availability: "stream", streaming_services: ["Prime Video"] })[0];
  expect(chip.label).toBe("📺 Streaming on Prime Video");
  expect(chip.clear).toEqual({ availability: "any", streaming_services: [] });
  expect(filterChips({ ...emptyCriteria(), availability: "stream" })[0].label).toBe("📺 Streaming (DE)");
});
