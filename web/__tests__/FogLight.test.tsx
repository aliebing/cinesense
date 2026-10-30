import { render } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";
import FogLight from "@/components/atmosphere/FogLight";
import { mockMatchMedia } from "./fixtures";

it("drops the fast near fog layer itself under reduced motion", () => {
  mockMatchMedia((q) => q.includes("prefers-reduced-motion"));
  const { container } = render(<FogLight tint="#1b4a6b" />);
  expect(container.querySelector(".fog--near")).toBeNull();
  expect(container.querySelector(".fog--far")).not.toBeNull();
});

it("gives every fog layer a static base opacity so it stays dim without animation", () => {
  const css = readFileSync(join(__dirname, "../app/atmosphere.css"), "utf8");
  for (const layer of ["far", "mid", "near"]) {
    const rule = css.match(new RegExp(`\\.fog--${layer} i \\{[^}]*\\}`));
    expect(rule?.[0], layer).toMatch(/opacity:\s*0?\.\d+/);
  }
});

it("lights the scene with two soft spotlights from the top corners instead of lens-flare dots", () => {
  mockMatchMedia(() => false);
  const { container } = render(<FogLight tint="#1b4a6b" />);
  expect(container.querySelector(".spot--left")).not.toBeNull();
  expect(container.querySelector(".spot--right")).not.toBeNull();
  expect(container.querySelector(".flare, .streak, .backlight")).toBeNull();
});
