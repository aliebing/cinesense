import { render, screen } from "@testing-library/react";
import { emptyCriteria, setSearchState } from "@/lib/searchState";
import { expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));
vi.mock("@/lib/api", () => ({
  getTags: () => Promise.resolve({ ok: true, data: [] }),
  search: (c: { person?: string | null; title?: string | null }) =>
    Promise.resolve({
      ok: true,
      data: {
        items: [],
        total: 0,
        hidden_by_exclusion: 0,
        extended_used: false,
        corrected_person: c.person === "sandra bullok" ? "Sandra Bullock" : null,
        corrected_title: c.title === "inceptoin" ? "Inception" : null,
        hidden_by: { "genre:Horror": 0 },
      },
    }),
  discover: () => Promise.resolve({ ok: true, data: { items: [], total: 0, hidden_by_exclusion: 0, extended_used: false } }),
}));

import ResultsPage from "@/app/results/page";

it("the search page leads back to the start page through the breadcrumb, without a second back button", async () => {
  render(<ResultsPage />);
  expect(await screen.findByRole("link", { name: "CineSense" })).toHaveAttribute("href", "/");
  expect(screen.queryByRole("link", { name: /Back to/ })).toBeNull();
});

it("autocorrects a misspelt person and title to the names the search found", async () => {
  setSearchState({ ...emptyCriteria(), person: "sandra bullok", title: "inceptoin" });
  render(<ResultsPage />);
  expect(await screen.findByText("👤 Sandra Bullock")).toBeInTheDocument();
  expect(await screen.findByText("🔤 “Inception”")).toBeInTheDocument();
  setSearchState(emptyCriteria());
});

it("passes what each exclusion hides on to the mood panel", async () => {
  setSearchState({ ...emptyCriteria(), person: "Sandra Bullock", exclude_genres: ["Horror"] });
  render(<ResultsPage />);
  expect(await screen.findByText("none of these films are Horror: changes nothing")).toBeInTheDocument();
  setSearchState(emptyCriteria());
});
