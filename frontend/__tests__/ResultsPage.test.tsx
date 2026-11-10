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

it("says in the exclusions row what each exclusion does in this search", async () => {
  setSearchState({ ...emptyCriteria(), person: "Sandra Bullock", exclude_genres: ["Horror"] });
  render(<ResultsPage />);
  const row = await screen.findByRole("region", { name: "Filters" });
  expect(await within(row).findByText("changes nothing here")).toBeInTheDocument();
  setSearchState(emptyCriteria());
});

it("shows the filters on top, then the moods; the advanced search opens on demand as a two-row box", async () => {
  setSearchState({ ...emptyCriteria(), tags: [{ idx: 1, weight: 6, mode: "must" }], year_from: 1990, year_to: 1999, exclude_people: ["Sylvester Stallone"] });
  render(<ResultsPage />);
  const moods = await screen.findByRole("region", { name: "Search criteria" });
  const row = screen.getByRole("region", { name: "Filters" });
  expect(row.compareDocumentPosition(moods) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy(); // filters first
  expect(within(moods).getByRole("button", { name: /Weight 3 of 5/ })).toBeInTheDocument(); // stars stay editable
  expect(within(moods).queryByText(/Sylvester Stallone/)).toBeNull(); // exclusions only in their own row
  expect(within(row).getByText(/without Sylvester Stallone/)).toBeInTheDocument();
  await userEvent.click(within(row).getByRole("button", { name: "Remove year range" }));
  expect(within(row).queryByText("1990–1999")).toBeNull();
  expect(screen.queryByRole("form", { name: "Advanced search" })).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: /Advanced search/ }));
  const adv = screen.getByRole("form", { name: "Advanced search" });
  expect(within(adv).getByRole("heading", { name: "Advanced search" })).toBeInTheDocument();
  expect(within(adv).getByLabelText("Title")).toBeInTheDocument(); // named for screen readers, shown as placeholder
  expect(within(adv).getByRole("group", { name: "Kind" })).toBeInTheDocument(); // the second row, no extra step
  setSearchState(emptyCriteria());
});


