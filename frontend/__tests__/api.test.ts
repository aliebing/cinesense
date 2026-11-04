import { describe, expect, it, vi } from "vitest";
import { getHome, getMovie, getWorldMovies } from "@/lib/api";

describe("apiGet", () => {
  it("maps fetch rejection to network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed")));
    expect(await getHome()).toEqual({ ok: false, error: "network" });
  });

  it("maps 404 to not_found", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 404 })));
    expect(await getMovie("x")).toEqual({ ok: false, error: "not_found" });
  });

  it("maps 500 to server", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 500 })));
    expect(await getWorldMovies("action")).toEqual({ ok: false, error: "server" });
  });

  it("returns parsed data on success and calls the API base URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "demo-01" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await getMovie("demo-01")).toEqual({ ok: true, data: { id: "demo-01" } });
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/movies/demo-01");
  });
});
