import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import RelatedRow from "@/components/genre/RelatedRow";
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
