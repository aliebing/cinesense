import { afterEach, expect, it, vi } from "vitest";
import { loadHome } from "@/lib/homeServer";
import { sampleHome } from "./fixtures";

afterEach(() => vi.unstubAllGlobals());

it("returns the rows the API sends", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(sampleHome))));
  expect(await loadHome()).toEqual(sampleHome);
});

it("returns null when the API is down or slow, so the browser asks itself", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("timeout")));
  expect(await loadHome()).toBeNull();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 503 })));
  expect(await loadHome()).toBeNull();
});
