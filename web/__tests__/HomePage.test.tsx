import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { mockMatchMedia, sampleHome, sampleRanked } from "./fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const getHome = vi.fn();
vi.mock("@/lib/api", () => ({
  getHome: () => getHome(),
  getTags: () => Promise.resolve({ ok: true, data: [] }),
  getProfile: () => Promise.resolve({ ok: true, data: { liked: [], disliked: [], taste: [] } }),
}));

import HomePage from "@/app/page";
import { clearChatLog, setChatLog } from "@/lib/chat";

beforeEach(() => {
  push.mockReset();
  getHome.mockReset();
  clearChatLog();
  mockMatchMedia(() => false);
});

it("shows the claim; no drifting tile rows and no speed toggle", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  expect(screen.getByText("Don't choose a movie.")).toBeInTheDocument();
  expect(screen.getByText("Choose a feeling.")).toBeInTheDocument();
  await screen.findByTestId("film-titles");
  expect(screen.queryByTestId("tile-row")).toBeNull();
  expect(screen.queryByRole("button", { name: /Speed/ })).toBeNull();
});

it("deals the agent's films as cards beside the chat, not inside it", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  act(() => setChatLog([{ role: "user", text: "dark" }, { role: "bot", text: "Here.", results: sampleRanked(4) }]));
  expect(await screen.findAllByTestId("dealt-card")).toHaveLength(4);
  expect(screen.queryByTestId("chat-pick")).toBeNull();
  expect(screen.getByText("Here.")).toBeInTheDocument();
});

it("shows the mood settings panel even before any tag is set", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  expect(screen.getByRole("heading", { name: "Your mood settings" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "+ Tag" })).toBeInTheDocument();
});

it("keeps claim and chat when the backend is unreachable", async () => {
  getHome.mockResolvedValue({ ok: false, error: "network" });
  render(<HomePage />);
  await waitFor(() => expect(screen.getByText("Couldn't load films")).toBeInTheDocument());
  expect(screen.getByText("Don't choose a movie.")).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "Message CineSense" })).toBeInTheDocument();
});

it("shows no film titles on narrow screens", async () => {
  mockMatchMedia((q) => q.includes("max-width: 759px"));
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  await waitFor(() => expect(getHome).toHaveBeenCalled());
  expect(screen.queryByTestId("film-titles")).toBeNull();
});

it("shows English quick filters without a language chip", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  const { container } = render(<HomePage />);
  const chips = [...container.querySelectorAll(".chat-chips button")].map((c) => c.textContent);
  expect(chips).toEqual(["🎬 In cinemas", "📺 Streaming", "🚫 No horror"]);
  expect(screen.queryByText(/Englisch|English/)).toBeNull();
});

it("the world label follows the hero world and advances after 12 s", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  const { container } = render(<HomePage />);
  const label = () => container.querySelector(".world-label")?.textContent ?? "";
  await waitFor(() => expect(label()).toContain("Suspense & Mystery"));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(12100);
  });
  expect(label()).toContain("Action & Adrenaline");
  vi.useRealTimers();
});

it("nav shortcuts open the results pre-filtered and 👤 opens the profile", async () => {
  getHome.mockResolvedValue({ ok: true, data: sampleHome });
  render(<HomePage />);
  const nav = screen.getByRole("navigation", { name: "Main navigation" });
  await userEvent.click(within(nav).getByRole("button", { name: "📺 Streaming" }));
  expect(push).toHaveBeenCalledWith("/results");
  expect(JSON.parse(window.sessionStorage.getItem("cinesense.search") ?? "{}").availability).toBe("stream");
  await userEvent.click(within(nav).getByRole("button", { name: "Profile" }));
  expect(await screen.findByRole("dialog", { name: "Your profile" })).toBeInTheDocument();
});
