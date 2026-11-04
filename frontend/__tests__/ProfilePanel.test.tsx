import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

const getProfile = vi.fn();
const resetProfile = vi.fn();
vi.mock("@/lib/api", () => ({ getProfile: () => getProfile(), resetProfile: () => resetProfile() }));

import ProfilePanel from "@/components/profile/ProfilePanel";

const profile = {
  liked: [{ id: "ml-1", title: "Moon", year: 2009 }],
  disliked: [{ id: "ml-2", title: "Titanic", year: 1997 }],
  taste: ["space travel", "dark"],
};

beforeEach(() => {
  getProfile.mockReset();
  resetProfile.mockReset();
});

it("shows what was learned and the rated films", async () => {
  getProfile.mockResolvedValue({ ok: true, data: profile });
  render(<ProfilePanel onClose={() => {}} />);
  expect(await screen.findByText("space travel · dark")).toBeInTheDocument();
  expect(screen.getByText("Moon (2009)")).toBeInTheDocument();
  expect(screen.getByText("Titanic (1997)")).toBeInTheDocument();
});

it("resets the profile", async () => {
  getProfile.mockResolvedValue({ ok: true, data: profile });
  resetProfile.mockResolvedValue({ ok: true, data: { liked: [], disliked: [], taste: [] } });
  render(<ProfilePanel onClose={() => {}} />);
  await userEvent.click(await screen.findByRole("button", { name: "Reset profile" }));
  expect(resetProfile).toHaveBeenCalled();
  expect(await screen.findByText(/Nothing learned yet/)).toBeInTheDocument();
});

it("explains the empty state", async () => {
  getProfile.mockResolvedValue({ ok: true, data: { liked: [], disliked: [], taste: [] } });
  render(<ProfilePanel onClose={() => {}} />);
  expect(await screen.findByText(/Nothing learned yet/)).toBeInTheDocument();
});
