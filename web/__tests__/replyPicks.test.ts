import { expect, it } from "vitest";
import { replyPicks } from "@/lib/chat";
import { sampleRanked } from "./fixtures";

it("a reply presents as many films as the agent says (3-5); older replies three", () => {
  const results = sampleRanked(8);
  expect(replyPicks({ role: "bot", text: "", results, picks: 5 })).toHaveLength(5);
  expect(replyPicks({ role: "bot", text: "", results })).toHaveLength(3);
  expect(replyPicks({ role: "user", text: "hi" })).toEqual([]);
});
