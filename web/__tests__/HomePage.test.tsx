import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { mockMatchMedia, sampleHome } from "./fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const getHome = vi.fn();
vi.mock("@/lib/api", () => ({ getHome: () => getHome() }));

import HomePage from "@/app/page";

beforeEach(() => {
  push.mockReset();
  getHome.mockReset();
  mockMatchMedia(() => false);
});

it("shows the claim and navigates to the genre page when a tile is clicked", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  expect(screen.getByText("Don't choose a movie.")).toBeInTheDocument();
  expect(screen.getByText("Choose a feeling.")).toBeInTheDocument();
  const tile = await screen.findAllByRole("button", { name: "Demo-Film 01" });
  await userEvent.click(tile[0]);
  expect(push).toHaveBeenCalledWith("/welt/action?film=demo-01");
});

it("keeps claim and chat when the backend is unreachable", async () => {
  getHome.mockResolvedValue({ ok: false, error: "network" });
  render(<HomePage />);
  await waitFor(() => expect(screen.getByText("Filme konnten nicht geladen werden")).toBeInTheDocument());
  expect(screen.getByText("Don't choose a movie.")).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "Nachricht an CineSense" })).toBeInTheDocument();
});

it("shows one tile strip and no film titles on narrow screens", async () => {
  mockMatchMedia((q) => q.includes("max-width: 759px"));
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  await screen.findAllByRole("button", { name: "Demo-Film 01" });
  expect(screen.getAllByTestId("tile-row")).toHaveLength(1);
  expect(screen.queryByTestId("film-titles")).toBeNull();
});
