import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { emptyCriteria, setSearchState } from "@/lib/searchState";
import { mockMatchMedia, sampleRanked } from "./fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const streamChat = vi.fn();
vi.mock("@/lib/chat", async (orig) => ({
  ...(await orig<typeof import("@/lib/chat")>()),
  streamChat: (...a: unknown[]) => streamChat(...a),
}));

import ChatPanel from "@/components/chat/ChatPanel";
import { clearChatLog } from "@/lib/chat";
import { useSearchState } from "@/lib/searchState";

function CriteriaProbe() {
  const [c] = useSearchState();
  return <output data-testid="criteria">{JSON.stringify(c)}</output>;
}

const final = (over = {}) => ({
  reply: "Here are dark picks.",
  criteria: { ...emptyCriteria(), tags: [{ idx: 7, weight: 8, mode: "prefer" }] },
  results: sampleRanked(4),
  proposals: [],
  handoff: null,
  usage: {},
  ...over,
});

beforeEach(() => {
  push.mockReset();
  streamChat.mockReset();
  clearChatLog();
  setSearchState(emptyCriteria());
  mockMatchMedia(() => false);
});

async function send(text: string) {
  await userEvent.type(screen.getByRole("textbox", { name: "Message CineSense" }), `${text}{Enter}`);
}

it("shows the status while waiting, then the reply and the top 3 picks", async () => {
  let resolve: (v: unknown) => void = () => {};
  streamChat.mockImplementation((_req, onStatus) => {
    onStatus("Searching plots…");
    return new Promise((r) => (resolve = r));
  });
  render(<ChatPanel mode="live" />);
  await send("something dark");
  expect(screen.getByText("something dark")).toBeInTheDocument();
  expect(await screen.findByText("Searching plots…")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  resolve(final());
  expect(await screen.findByText("Here are dark picks.")).toBeInTheDocument();
  expect(screen.getAllByTestId("chat-pick")).toHaveLength(3);
  expect(screen.queryByText("Searching plots…")).toBeNull();
});

it("writes the agent's criteria into the shared search state", async () => {
  streamChat.mockResolvedValue(final());
  render(
    <>
      <ChatPanel mode="live" />
      <CriteriaProbe />
    </>,
  );
  await send("dark");
  await waitFor(() => expect(screen.getByTestId("criteria").textContent).toContain('"idx":7'));
  expect(streamChat.mock.calls[0][0].criteria).toEqual(emptyCriteria());
});

it("adds a not-tag when a proposal is clicked", async () => {
  streamChat.mockResolvedValue(final({ proposals: [{ idx: 42, tag: "scary", mode: "not" }] }));
  render(
    <>
      <ChatPanel mode="live" />
      <CriteriaProbe />
    </>,
  );
  await send("nothing scary");
  await userEvent.click(await screen.findByRole("button", { name: "Also exclude scary" }));
  expect(screen.getByTestId("criteria").textContent).toContain('{"idx":42,"weight":5,"mode":"not"}');
  expect(screen.queryByRole("button", { name: "Also exclude scary" })).toBeNull();
});

it("navigates to the stage on hand-off", async () => {
  streamChat.mockResolvedValue(final({ handoff: { world_id: "scifi", film_id: "ml-1" } }));
  render(<ChatPanel mode="live" />);
  await send("show me Moon");
  await userEvent.click(await screen.findByRole("button", { name: "Show on stage →" }));
  expect(push).toHaveBeenCalledWith("/world/scifi?film=ml-1");
});

it("shows the error text and keeps the chips usable", async () => {
  const { ChatError } = await import("@/lib/chat");
  streamChat.mockRejectedValue(new ChatError("The assistant is unavailable right now."));
  render(<ChatPanel mode="live" />);
  await send("hi");
  expect(await screen.findByText("The assistant is unavailable right now.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "📺 Streaming" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Send" })).toBeEnabled();
});

it("keeps the conversation when the panel is mounted again (page change)", async () => {
  streamChat.mockResolvedValue(final());
  const { unmount } = render(<ChatPanel mode="live" />);
  await send("dark");
  await screen.findByText("Here are dark picks.");
  unmount();
  render(<ChatPanel mode="live" />);
  expect(screen.getByText("Here are dark picks.")).toBeInTheDocument();
});

it("a second panel (genre drawer) sees the turn in flight and cannot send", async () => {
  let resolve: (v: unknown) => void = () => {};
  streamChat.mockImplementation(() => new Promise((r) => (resolve = r)));
  render(
    <>
      <div data-testid="home">
        <ChatPanel mode="live" />
      </div>
    </>,
  );
  await send("dark");
  const { getAllByRole } = render(<ChatPanel mode="live" />);
  const sends = getAllByRole("button", { name: "Send" });
  expect(sends.every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
  resolve(final());
  await waitFor(() => expect(screen.getAllByText("Here are dark picks.").length).toBeGreaterThan(0));
});

it("disables quick chips while the agent works so its answer can't undo them", async () => {
  let resolve: (v: unknown) => void = () => {};
  streamChat.mockImplementation(() => new Promise((r) => (resolve = r)));
  render(<ChatPanel mode="live" />);
  await send("dark");
  expect(screen.getByRole("button", { name: "📺 Streaming" })).toBeDisabled();
  resolve(final());
  await waitFor(() => expect(screen.getByRole("button", { name: "📺 Streaming" })).toBeEnabled());
});

it("appends the reply to the latest log instead of an old snapshot", async () => {
  const { setChatLog } = await import("@/lib/chat");
  let resolve: (v: unknown) => void = () => {};
  streamChat.mockImplementation(() => new Promise((r) => (resolve = r)));
  render(<ChatPanel mode="live" />);
  await send("dark");
  const { getChatLog } = await import("@/lib/chat");
  setChatLog([...getChatLog(), { role: "bot", text: "note added meanwhile" }]);
  resolve(final());
  expect(await screen.findByText("Here are dark picks.")).toBeInTheDocument();
  expect(screen.getByText("note added meanwhile")).toBeInTheDocument();
});

it("typing in the chat pauses the page's motion; leaving the field resumes it", async () => {
  render(<ChatPanel mode="live" />);
  await userEvent.type(screen.getByRole("textbox", { name: "Message CineSense" }), "funny");
  expect(document.documentElement.hasAttribute("data-typing")).toBe(true);
  await userEvent.tab();
  expect(document.documentElement.hasAttribute("data-typing")).toBe(false);
});
