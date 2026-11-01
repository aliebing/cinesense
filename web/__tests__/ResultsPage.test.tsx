import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));
vi.mock("@/lib/api", () => ({
  getTags: () => Promise.resolve({ ok: true, data: [] }),
  search: () => Promise.resolve({ ok: true, data: { items: [], total: 0, hidden_by_exclusion: 0, extended_used: false } }),
  discover: () => Promise.resolve({ ok: true, data: { items: [], total: 0, hidden_by_exclusion: 0, extended_used: false } }),
}));

import ResultsPage from "@/app/results/page";

it("the search page leads back to the start page with the results", async () => {
  render(<ResultsPage />);
  expect(await screen.findByRole("link", { name: "← Back to results" })).toHaveAttribute("href", "/");
});
