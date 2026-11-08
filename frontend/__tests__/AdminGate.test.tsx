import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/admin/tech" }));

const adminMe = vi.fn();
const adminLogin = vi.fn();
const adminLogout = vi.fn();
vi.mock("@/lib/admin", async (orig) => ({
  ...(await orig<typeof import("@/lib/admin")>()),
  adminMe: () => adminMe(),
  adminLogin: (n: string, p: string) => adminLogin(n, p),
  adminLogout: () => adminLogout(),
}));

import AdminGate from "@/components/admin/AdminGate";

beforeEach(() => vi.clearAllMocks());

it("asks for name and password, then shows the admin pages", async () => {
  adminMe.mockResolvedValueOnce({ ok: false, status: 401 }).mockResolvedValue({ ok: true, name: "admin" });
  adminLogin.mockResolvedValue({ ok: true, name: "admin" });
  render(<AdminGate>secret page</AdminGate>);
  await userEvent.type(await screen.findByLabelText("Name"), "admin");
  await userEvent.type(screen.getByLabelText("Password"), "pw");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(adminLogin).toHaveBeenCalledWith("admin", "pw");
  expect(await screen.findByText("secret page")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
});

it("says when the password is wrong and keeps the pages hidden", async () => {
  adminMe.mockResolvedValue({ ok: false, status: 401 });
  adminLogin.mockResolvedValue({ ok: false, status: 401 });
  render(<AdminGate>secret page</AdminGate>);
  await userEvent.type(await screen.findByLabelText("Name"), "admin");
  await userEvent.type(screen.getByLabelText("Password"), "nope");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Name or password is wrong.");
  expect(screen.queryByText("secret page")).toBeNull();
});

it("signing out returns to the form", async () => {
  adminMe.mockResolvedValueOnce({ ok: true, name: "admin" }).mockResolvedValue({ ok: false, status: 401 });
  adminLogout.mockResolvedValue({ ok: true, name: "" });
  render(<AdminGate>secret page</AdminGate>);
  await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
  expect(await screen.findByLabelText("Password")).toBeInTheDocument();
  expect(screen.queryByText("secret page")).toBeNull();
});
