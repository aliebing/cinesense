import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";

it("shows the new image after a previous src failed to load", () => {
  const { rerender } = render(<ImageOrPlaceholder src="https://example.test/a.jpg" alt="Poster A" />);
  fireEvent.error(screen.getByAltText("Poster A"));
  expect(screen.getByTestId("image-placeholder")).toBeInTheDocument();
  rerender(<ImageOrPlaceholder src="https://example.test/b.jpg" alt="Poster B" />);
  expect(screen.getByAltText("Poster B")).toHaveAttribute("src", "https://example.test/b.jpg");
});
