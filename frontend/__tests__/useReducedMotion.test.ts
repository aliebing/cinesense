import { renderHook } from "@testing-library/react";
import { expect, it } from "vitest";
import { useReducedMotion } from "@/lib/useReducedMotion";
import { mockMatchMedia } from "./fixtures";

it("returns true when the reduced-motion media query matches", () => {
  mockMatchMedia((q) => q.includes("prefers-reduced-motion"));
  const { result } = renderHook(() => useReducedMotion());
  expect(result.current).toBe(true);
});

it("returns false otherwise", () => {
  mockMatchMedia(() => false);
  const { result } = renderHook(() => useReducedMotion());
  expect(result.current).toBe(false);
});
