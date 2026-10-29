import { act, render, screen, waitFor } from "@testing-library/react";
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
  expect(push).toHaveBeenCalledWith("/world/action?film=demo-01");
});

it("keeps claim and chat when the backend is unreachable", async () => {
  getHome.mockResolvedValue({ ok: false, error: "network" });
  render(<HomePage />);
  await waitFor(() => expect(screen.getByText("Couldn't load films")).toBeInTheDocument());
  expect(screen.getByText("Don't choose a movie.")).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "Message CineSense" })).toBeInTheDocument();
});

it("shows one tile strip and no film titles on narrow screens", async () => {
  mockMatchMedia((q) => q.includes("max-width: 759px"));
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  await screen.findAllByRole("button", { name: "Demo-Film 02" });
  expect(screen.getAllByTestId("tile-row")).toHaveLength(1);
  expect(screen.queryByTestId("film-titles")).toBeNull();
});

it("shows English quick filters without a language chip", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  const { container } = render(<HomePage />);
  const chips = [...container.querySelectorAll(".chat-chips span")].map((c) => c.textContent);
  expect(chips).toEqual(["🎬 In cinemas", "📺 Streaming", "🚫 No horror"]);
  expect(screen.queryByText(/Englisch|English/)).toBeNull();
});

it("top tile row follows the hero world and advances after 12 s", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  const firstLabel = async () => (await screen.findAllByRole("link", { name: /Suspense|Action/ }))[0];
  expect((await firstLabel()).textContent).toBe("Suspense & Mystery");
  await act(async () => {
    await vi.advanceTimersByTimeAsync(12100);
  });
  expect(screen.getAllByTestId("tile-row")[0].closest(".tile-row-wrap")!.textContent).toContain("Action & Adrenaline");
  vi.useRealTimers();
});
