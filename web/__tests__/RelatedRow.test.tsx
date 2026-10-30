import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import RelatedRow, { turnPage } from "@/components/genre/RelatedRow";
import { mockMatchMedia, sampleRanked } from "./fixtures";

beforeEach(() => mockMatchMedia(() => false));

it("shows match badges and selects a film on click", async () => {
  const onSelect = vi.fn();
  render(<RelatedRow items={sampleRanked(3)} onSelect={onSelect} />);
  expect(screen.getAllByText("90%").length).toBeGreaterThan(0);
  await userEvent.click(screen.getAllByRole("button", { name: /Demo-Film 02/ })[0]);
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "demo-02" }));
});

it("renders a placeholder for a film without poster", () => {
  const items = sampleRanked(1);
  items[0] = { ...items[0], movie: { ...items[0].movie, poster_url: null } };
  render(<RelatedRow items={items} onSelect={() => {}} />);
  expect(screen.getAllByTestId("image-placeholder").length).toBeGreaterThan(0);
});

it("shows six films at a time and » slides a completely new set in", async () => {
  render(<RelatedRow items={sampleRanked(14)} onSelect={() => {}} />);
  const visible = () => screen.getAllByRole("button", { name: /Demo-Film/ }).map((b) => b.getAttribute("aria-label")!.split(",")[0]);
  expect(visible()).toHaveLength(6);
  expect(screen.getByText("1 / 3")).toBeInTheDocument();
  const first = visible();
  await userEvent.click(screen.getByRole("button", { name: "Next films" }));
  expect(screen.getByText("2 / 3")).toBeInTheDocument();
  expect(visible().some((t) => first.includes(t))).toBe(false);
  await userEvent.click(screen.getByRole("button", { name: "Next films" }));
  expect(visible()).toHaveLength(2); // last page
  await userEvent.click(screen.getByRole("button", { name: "Next films" }));
  expect(screen.getByText("1 / 3")).toBeInTheDocument(); // wraps around
  await userEvent.click(screen.getByRole("button", { name: "Previous films" }));
  expect(screen.getByText("3 / 3")).toBeInTheDocument();
});

it("turnPage wraps in both directions", () => {
  expect(turnPage(2, 1, 3)).toBe(0);
  expect(turnPage(0, -1, 3)).toBe(2);
  expect(turnPage(0, 1, 0)).toBe(0);
});
