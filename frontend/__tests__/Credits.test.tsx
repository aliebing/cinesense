import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import CreditsPage from "@/app/credits/page";

it("lists every data source with its licence link, plus YouTube terms and privacy note", () => {
  render(<CreditsPage />);
  for (const name of ["MovieLens", "Wikidata", "Wikipedia", "Streaming Availability API", "YouTube", "Unsplash"]) {
    expect(screen.getAllByText(new RegExp(name)).length).toBeGreaterThan(0);
  }
  expect(screen.getByRole("link", { name: "YouTube Terms of Service" })).toHaveAttribute("href", "https://www.youtube.com/t/terms");
  expect(screen.getByRole("link", { name: "Google Privacy Policy" })).toHaveAttribute("href", "https://policies.google.com/privacy");
  expect(screen.getByText(/not use TMDB/)).toBeInTheDocument();
});
