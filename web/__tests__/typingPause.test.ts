import { afterEach, expect, it, vi } from "vitest";
import { isTyping, noteTyping, stopTyping } from "@/lib/typingPause";

afterEach(() => {
  stopTyping();
  vi.useRealTimers();
});

it("a keystroke pauses the motion until 1.5 s after the last one", () => {
  vi.useFakeTimers();
  noteTyping();
  expect(isTyping()).toBe(true);
  expect(document.documentElement.hasAttribute("data-typing")).toBe(true);
  vi.advanceTimersByTime(1000);
  noteTyping(); // still typing: the pause is extended
  vi.advanceTimersByTime(1000);
  expect(isTyping()).toBe(true);
  vi.advanceTimersByTime(600);
  expect(isTyping()).toBe(false);
  expect(document.documentElement.hasAttribute("data-typing")).toBe(false);
});

it("stopTyping resumes at once (blur, send)", () => {
  noteTyping();
  stopTyping();
  expect(isTyping()).toBe(false);
});
