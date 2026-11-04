import { expect, it } from "vitest";
import { replyPicks } from "@/lib/chat";
import { sampleRanked } from "./fixtures";

it("a reply presents as many films as the agent says (3-5); older replies three", () => {
  const results = sampleRanked(8);
  expect(replyPicks({ role: "bot", text: "", results, picks: 5 })).toHaveLength(5);
  expect(replyPicks({ role: "bot", text: "", results })).toHaveLength(3);
  expect(replyPicks({ role: "user", text: "hi" })).toEqual([]);
});

it("the chat's picks lead the rows only while the criteria are still the ones the chat set", async () => {
  const { currentPicks } = await import("@/lib/chat");
  const { emptyCriteria } = await import("@/lib/searchState");
  const set = { ...emptyCriteria(), tags: [{ idx: 7, weight: 6, mode: "prefer" as const }] };
  const log = [
    { role: "user" as const, text: "funny" },
    { role: "bot" as const, text: "", results: sampleRanked(5), picks: 4, criteria: set },
  ];
  expect(currentPicks(log, { ...set, world_id: "comedy" })).toHaveLength(4); // the world never matters
  expect(currentPicks(log, { ...set, tags: [{ idx: 7, weight: 10, mode: "prefer" }] })).toEqual([]); // edited
  expect(currentPicks([...log, { role: "bot", text: "sorry", error: true }], set)).toHaveLength(4);
});
