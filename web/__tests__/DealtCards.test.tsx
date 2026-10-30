import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { mockMatchMedia, sampleRanked } from "./fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));

import DealtCards from "@/components/home/DealtCards";
import { clearChatLog, setChatLog, setChatStatus } from "@/lib/chat";

beforeEach(() => {
  push.mockReset();
  clearChatLog();
  setChatStatus(null);
  mockMatchMedia(() => false);
});

it("shows nothing before the agent has answered", () => {
  render(<DealtCards />);
  expect(screen.queryByTestId("dealt-card")).toBeNull();
  expect(screen.queryByTestId("deal-deck")).toBeNull();
});

it("shows the deck while the agent works", () => {
  render(<DealtCards />);
  act(() => setChatStatus("Ranking films…"));
  expect(screen.getByTestId("deal-deck")).toBeInTheDocument();
});

it("lays out up to 8 cards of the latest reply, each with match and reason; click opens the stage", async () => {
  const results = sampleRanked(10).map((r, i) => ({ ...r, reasons: i === 0 ? ["dark 91%", "plot: lonely"] : [] }));
  render(<DealtCards />);
  act(() => setChatLog([{ role: "user", text: "dark" }, { role: "bot", text: "Here.", results }]));
  const cards = await screen.findAllByTestId("dealt-card");
  expect(cards).toHaveLength(8);
  expect(cards[0]).toHaveTextContent("Demo-Film 01");
  expect(cards[0]).toHaveTextContent("90%");
  expect(cards[0]).toHaveTextContent("dark 91%");
  expect(cards[0]).not.toHaveTextContent("plot: lonely");
  await userEvent.click(screen.getByRole("button", { name: "Open Demo-Film 02" }));
  expect(push).toHaveBeenCalledWith("/world/suspense?film=demo-02");
});

it("replaces the cards when a newer reply arrives", async () => {
  render(<DealtCards />);
  act(() => setChatLog([{ role: "bot", text: "A", results: sampleRanked(2) }]));
  expect(await screen.findAllByTestId("dealt-card")).toHaveLength(2);
  act(() =>
    setChatLog([
      { role: "bot", text: "A", results: sampleRanked(2) },
      { role: "user", text: "more" },
      { role: "bot", text: "B", results: sampleRanked(5) },
    ]),
  );
  await waitFor(() => expect(screen.getAllByTestId("dealt-card")).toHaveLength(5));
});

it("keeps the last cards when a reply has no films (a clarifying question)", async () => {
  render(<DealtCards />);
  act(() => setChatLog([{ role: "bot", text: "A", results: sampleRanked(3) }]));
  expect(await screen.findAllByTestId("dealt-card")).toHaveLength(3);
  act(() => setChatLog([{ role: "bot", text: "A", results: sampleRanked(3) }, { role: "bot", text: "Which decade?" }]));
  expect(screen.getAllByTestId("dealt-card")).toHaveLength(3);
});
