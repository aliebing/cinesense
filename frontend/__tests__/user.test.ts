import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
  window.localStorage.clear();
});

it("creates an id without crypto.randomUUID (plain http on a LAN address)", async () => {
  vi.stubGlobal("crypto", { getRandomValues: (a: Uint8Array) => a.fill(7) });
  const { userId } = await import("@/lib/user");
  const id = userId();
  expect(id).toMatch(/^[0-9a-f-]{36}$/);
  expect(userId()).toBe(id);
});
