import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { emptyCriteria, setSearchState } from "@/lib/searchState";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

import ChatDrawer from "@/components/genre/ChatDrawer";
import { useSearchState } from "@/lib/searchState";

function Probe() {
  const [c] = useSearchState();
  return <output data-testid="c">{JSON.stringify(c.tags)}</output>;
}

beforeEach(() => setSearchState(emptyCriteria()));

it("the drawer's No horror chip also sets the horror not-tag", async () => {
  render(
    <>
      <ChatDrawer horrorIdx={521} />
      <Probe />
    </>,
  );
  await userEvent.click(screen.getByRole("button", { name: "💬 Chat" }));
  await userEvent.click(screen.getByRole("button", { name: "🚫 No horror" }));
  expect(screen.getByTestId("c").textContent).toContain('"idx":521');
});
