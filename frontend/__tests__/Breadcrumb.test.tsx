import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Breadcrumb from "@/components/nav/Breadcrumb";

it("leads home, links the steps in between and marks the current page", () => {
  render(<Breadcrumb items={[{ label: "Search", href: "/results" }, { label: "Inception", href: "/x" }]} />);
  expect(screen.getByRole("link", { name: "CineSense" })).toHaveAttribute("href", "/");
  expect(screen.getByRole("link", { name: "Search" })).toHaveAttribute("href", "/results");
  expect(screen.queryByRole("link", { name: "Inception" })).toBeNull();
  expect(screen.getByText("Inception")).toHaveAttribute("aria-current", "page");
});
