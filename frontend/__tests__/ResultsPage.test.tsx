import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  await userEvent.click(await screen.findByRole("button", { name: /Edit moods & filters/ }));
  expect(await screen.findByText("none of these films are Horror: changes nothing")).toBeInTheDocument();
  setSearchState(emptyCriteria());
});

it("shows the search as one line of chips and opens the full mood panel on demand", async () => {
  setSearchState({ ...emptyCriteria(), tags: [{ idx: 1, weight: 6, mode: "must" }], year_from: 1990, year_to: 1999, exclude_people: ["Sylvester Stallone"] });
  render(<ResultsPage />);
  const bar = await screen.findByRole("region", { name: "Your search" });
  expect(within(bar).getByText("1990–1999")).toBeInTheDocument();
  expect(within(bar).getByText(/without Sylvester Stallone/)).toBeInTheDocument();
  expect(within(bar).getByText("must")).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Search criteria" })).toBeNull(); // the full panel stays closed
  await userEvent.click(within(bar).getByRole("button", { name: /Edit moods & filters/ }));
  expect(screen.getByRole("region", { name: "Search criteria" })).toBeInTheDocument();
  await userEvent.click(within(bar).getByRole("button", { name: "Remove year range" }));
  expect(within(bar).queryByText("1990–1999")).toBeNull();
  setSearchState(emptyCriteria());
});

it("opens the full mood panel at once when there is no search yet", async () => {
  setSearchState(emptyCriteria());
  render(<ResultsPage />);
  expect(await screen.findByRole("region", { name: "Search criteria" })).toBeInTheDocument();
});
