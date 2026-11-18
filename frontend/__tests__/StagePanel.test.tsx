import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
const reportTrailer = vi.fn();
vi.mock("@/lib/api", () => ({ reportTrailer: (id: string) => reportTrailer(id) }));

import StagePanel from "@/components/genre/StagePanel";
import { sampleMovies, sampleWorlds } from "./fixtures";

const base = sampleMovies(1)[0];
const world = sampleWorlds[1];

it("shows a note instead of an iframe when there is no trailer", () => {
  render(<StagePanel movie={{ ...base, youtube_key: null }} world={world} why="Test" />);
  expect(screen.getByText("No official trailer available")).toBeInTheDocument();
  expect(screen.queryByTitle(/Official trailer/)).toBeNull();
});

it("loads the youtube-nocookie embed only after clicking play", async () => {
  render(<StagePanel movie={{ ...base, youtube_key: "abc123" }} world={world} why="Test" />);
  expect(screen.queryByTitle(/Official trailer/)).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: /Play trailer/ }));
  const iframe = screen.getByTitle("Official trailer: Demo-Film 01");
  expect(iframe.getAttribute("src")).toContain("youtube-nocookie.com/embed/abc123");
});

it("labels the placeholder trailer", () => {
  render(<StagePanel movie={{ ...base, youtube_key: "placeholder" }} world={world} why="Test" />);
  expect(screen.getByText("Placeholder trailer")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Play trailer/ })).toBeNull();
});

it("shows streaming providers, TMDB rating, badge and why text", async () => {
  const movie = {
    ...base,
    ml_rating: 4.06,
    ml_rating_count: 12345,
    availability: {
      in_cinema_de: false,
      streaming_de: [
        { service: "Netflix", type: "subscription" as const, link: null },
        { service: "Disney+", type: "subscription" as const, link: null },
      ],
      subscription_services: ["Netflix", "Disney+"],
    },
  };
  render(<StagePanel movie={movie} world={world} why="Highly rated" />);
  expect(screen.getByText("📺 Netflix")).toBeInTheDocument();
  expect(screen.getByText("📺 Disney+")).toBeInTheDocument();
  expect(screen.getByText("⭐ MovieLens 4.1/5 (12,345 ratings)")).toBeInTheDocument();
  expect(screen.getByText("Placeholder", { selector: "span" })).toBeInTheDocument();
  expect(screen.getByText("Highly rated")).toBeInTheDocument();
  expect(screen.queryByText("🎬 In cinemas")).toBeNull();
});

it("renders the four feedback buttons disabled", () => {
  render(<StagePanel movie={base} world={world} why="Test" />);
  const names = ["👍 More like this", "👎 Not for me", "⚡ More action", "😂 Funnier"];
  for (const name of names) expect(screen.getByRole("button", { name })).toBeDisabled();
});

it("shows the four actions as icon buttons with their full name as label and tooltip", () => {
  render(<StagePanel movie={base} world={world} why="Test" />);
  const names = ["👍 More like this", "👎 Not for me", "⚡ More action", "😂 Funnier"];
  const buttons = names.map((name) => screen.getByRole("button", { name }));
  expect(buttons.map((b) => b.textContent)).toEqual(["👍", "👎", "⚡", "😂"]);
  expect(buttons.map((b) => b.getAttribute("title"))).toEqual(["More like this", "Not for me", "More action (only for this session)", "Funnier (only for this session)"]);
});


it("streaming states: unknown, not in Germany, and rent/buy collapsed", async () => {
  const { rerender } = render(<StagePanel movie={{ ...base, availability: { in_cinema_de: false, streaming_de: null, subscription_services: [] } }} world={world} why="x" />);
  expect(screen.getByText("Streaming not checked yet")).toHaveClass("stage-tag--unchecked");
  rerender(<StagePanel movie={{ ...base, availability: { in_cinema_de: false, streaming_de: [], subscription_services: [] } }} world={world} why="x" />);
  expect(screen.getByText("Not streaming in Germany")).toBeInTheDocument();
  rerender(
    <StagePanel
      movie={{
        ...base,
        availability: {
          in_cinema_de: false,
          streaming_de: [
            { service: "Netflix", type: "subscription", link: null },
            { service: "Apple TV", type: "rent", link: null },
            { service: "Prime Video", type: "buy", link: null },
          ],
          subscription_services: ["Netflix"],
        },
      }}
      world={world}
      why="x"
    />,
  );
  expect(screen.getByText("🛒 Rent/buy: Apple TV")).toBeInTheDocument();
  expect(screen.getByText("🛒 Rent/buy: Prime Video")).toBeInTheDocument();
});

it("links each offer to the provider, once per service, and offers a search when nothing is known", async () => {
  const link = "https://www.amazon.de/gp/video/detail/X";
  const { rerender } = render(
    <StagePanel
      movie={{
        ...base,
        availability: {
          in_cinema_de: false,
          streaming_de: [
            { service: "Prime Video", type: "buy", link },
            { service: "Prime Video", type: "rent", link: "https://other" },
          ],
          subscription_services: [],
        },
      }}
      world={world}
      why="x"
    />,
  );
  expect(screen.getByRole("link", { name: "🛒 Rent/buy: Prime Video" })).toHaveAttribute("href", link);
  rerender(<StagePanel movie={{ ...base, title: "Get Out Your Handkerchiefs (Préparez vos mouchoirs)", availability: { in_cinema_de: false, streaming_de: [], subscription_services: [] } }} world={world} why="x" />);
  expect(screen.getByRole("link", { name: "Find where to watch ↗" })).toHaveAttribute(
    "href",
    "https://www.justwatch.com/de/Suche?q=Get%20Out%20Your%20Handkerchiefs",
  );
});

it("links to IMDb and Wikipedia and shows people, tags and German cinema release", async () => {
  render(
    <StagePanel
      movie={{ ...base, imdb_id: "tt0816692", wikipedia_title: "Interstellar (film)", directors: ["Christopher Nolan"], cast_top: ["Matthew McConaughey"], top_tags: ["space travel"], release_date_de: "2026-10-01", availability: { in_cinema_de: true, streaming_de: null, subscription_services: [] } }}
      world={world}
      why="x"
    />,
  );
  expect(screen.getByRole("link", { name: "IMDb ↗" })).toHaveAttribute("href", "https://www.imdb.com/title/tt0816692/");
  expect(screen.getByRole("link", { name: "Wikipedia ↗" })).toHaveAttribute("href", "https://en.wikipedia.org/wiki/Interstellar_(film)");
  expect(screen.getByText(/Christopher Nolan/)).toBeInTheDocument();
  expect(screen.getByText("space travel")).toBeInTheDocument();
  expect(screen.getByText("🎬 In cinemas (German release 2026-10-01)")).toBeInTheDocument();
});

it("the stage trailer stops when a hover trailer starts (one audio source)", async () => {
  const { resetActiveTrailer, useActiveTrailer } = await import("@/lib/useActiveTrailer");
  resetActiveTrailer();
  function Hover() {
    const { activate } = useActiveTrailer();
    return (
      <button type="button" onClick={() => activate("hover-x")}>
        hover
      </button>
    );
  }
  render(
    <>
      <StagePanel movie={{ ...base, youtube_key: "abc123" }} world={world} why="x" />
      <Hover />
    </>,
  );
  await userEvent.click(screen.getByRole("button", { name: /Play trailer/ }));
  expect(screen.getByTitle("Official trailer: Demo-Film 01")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "hover" }));
  expect(screen.queryByTitle("Official trailer: Demo-Film 01")).toBeNull();
});


it("a blocked stage trailer falls back to the image with a YouTube link and is reported", async () => {
  const { act } = await import("@testing-library/react");
  reportTrailer.mockReset();
  render(<StagePanel movie={{ ...base, youtube_key: "blockedDE1" }} world={world} why="Test" />);
  await userEvent.click(screen.getByRole("button", { name: /Play trailer/ }));
  expect(screen.getByTitle("Official trailer: Demo-Film 01").getAttribute("src")).toContain("enablejsapi=1");
  act(() => {
    window.dispatchEvent(
      new MessageEvent("message", { origin: "https://www.youtube-nocookie.com", data: '{"event":"onError","info":150}' }),
    );
  });
  expect(screen.queryByTitle(/Official trailer/)).toBeNull();
  expect(screen.getByText(/can.t be played here/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Watch on YouTube" })).toHaveAttribute("href", "https://www.youtube.com/watch?v=blockedDE1");
  expect(reportTrailer).toHaveBeenCalledWith("blockedDE1");
});

it("a page kept alive in the background (Next keeps visited routes hidden) stops its trailer", async () => {
  const { Activity } = await import("react");
  const { act } = await import("@testing-library/react");
  const { resetActiveTrailer } = await import("@/lib/useActiveTrailer");
  resetActiveTrailer();
  const movie = { ...base, youtube_key: "abc123" };
  const { rerender } = render(
    <Activity mode="visible">
      <StagePanel movie={movie} world={world} why="Test" />
    </Activity>,
  );
  await userEvent.click(screen.getByRole("button", { name: /Play trailer/ }));
  const iframe = screen.getByTitle("Official trailer: Demo-Film 01") as HTMLIFrameElement;
  act(() =>
    rerender(
      <Activity mode="hidden">
        <StagePanel movie={movie} world={world} why="Test" />
      </Activity>,
    ),
  );
  expect(iframe.getAttribute("src")).toBe("about:blank"); // silent at once, even before React re-renders it
  act(() =>
    rerender(
      <Activity mode="visible">
        <StagePanel movie={movie} world={world} why="Test" />
      </Activity>,
    ),
  );
  expect(screen.getByRole("button", { name: /Play trailer/ })).toBeInTheDocument(); // back: nothing autoplays
});

it("shows the German title under the title when Wikidata knows one", () => {
  render(<StagePanel movie={{ ...base, title: "Apache Gold", title_de: "Winnetou 1. Teil" }} world={world} why="Test" />);
  expect(screen.getByText("Winnetou 1. Teil")).toHaveClass("stage-title-de");
});

it("shows no German line when it equals the title", () => {
  render(<StagePanel movie={{ ...base, title: "Old Shatterhand", title_de: "Old Shatterhand" }} world={world} why="Test" />);
  expect(document.querySelector(".stage-title-de")).toBeNull();
});

it("shows In cinemas and Placeholder", () => {
  const movie = { ...base, is_placeholder: true, release_date_de: "2026-12-01", availability: { ...base.availability, in_cinema_de: true } };
  render(<StagePanel movie={movie} world={world} why="x" />);
  expect(screen.getByText("🎬 In cinemas (German release 2026-12-01)")).toBeInTheDocument();
  expect(screen.getByText("Placeholder", { selector: "span" })).toBeInTheDocument();
});

it("shows the plot once after another film comes on stage", () => {
  const { rerender } = render(<StagePanel movie={base} world={world} why="x" />);
  rerender(<StagePanel movie={{ ...base, id: "other" }} world={world} why="x" />);
  expect(document.querySelectorAll(".stage-overview")).toHaveLength(1);
});

const film = { ...base, overview: "A lone worker on the Moon nears the end of his contract.", ml_rating: 4.06, ml_rating_count: 12345, directors: ["Duncan Jones"], cast_top: ["Sam Rockwell"], imdb_id: "tt1", wikipedia_title: "Moon (film)", top_tags: ["space", "loneliness"] };

it("shows everything in the box in order: meta, people, why, full plot, rating", () => {
  render(<StagePanel movie={film} world={world} why="Fits" />);
  const body = document.querySelector(".stage-info__body") as HTMLElement;
  expect(body).not.toBeNull();
  const order = ["2020 · 2 h 0 min · EN (original)", "Directed by Duncan Jones · with Sam Rockwell", "Fits", "A lone worker on the Moon nears the end of his contract.", "⭐ MovieLens 4.1/5 (12,345 ratings)"];
  const nodes = order.map((t) => within(body).getByText(t));
  for (let i = 1; i < nodes.length; i++)
    expect(nodes[i - 1].compareDocumentPosition(nodes[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.queryByRole("button", { name: "More" })).toBeNull();
  expect(screen.queryByRole("button", { name: /More info/ })).toBeNull();
});

it("puts IMDb, Wikipedia and where to watch in the box footer after Links:", () => {
  render(<StagePanel movie={{ ...film, availability: { in_cinema_de: false, streaming_de: null, subscription_services: [] } }} world={world} why="x" />);
  const foot = document.querySelector(".stage-info__foot") as HTMLElement;
  expect(foot).not.toBeNull();
  expect(within(foot).getByText("Links:")).toBeInTheDocument();
  expect(within(foot).getByRole("link", { name: "IMDb ↗" })).toBeInTheDocument();
  expect(within(foot).getByRole("link", { name: "Wikipedia ↗" })).toBeInTheDocument();
  expect(within(foot).getByText("Streaming not checked yet")).toBeInTheDocument();
  expect(within(foot).getByText("Find where to watch ↗")).toBeInTheDocument();
});

it("shows mood tags and the four actions in a strip under the trailer", () => {
  render(<StagePanel movie={film} world={world} why="x" />);
  const screenCol = document.querySelector(".stage-screen") as HTMLElement;
  expect(screenCol).not.toBeNull();
  expect(screenCol.querySelector(".stage-trailer")).not.toBeNull();
  const strip = within(screenCol).getByText("Mood tags:").closest(".stage-strip") as HTMLElement;
  expect(within(strip).getByText("space")).toBeInTheDocument();
  expect(within(strip).getByText("loneliness")).toBeInTheDocument();
  for (const name of ["👍 More like this", "👎 Not for me", "⚡ More action", "😂 Funnier"])
    expect(within(strip).getByRole("button", { name })).toBeInTheDocument();
});

it("leaves the Mood tags label out when a film has none", () => {
  render(<StagePanel movie={{ ...film, top_tags: [] }} world={world} why="x" />);
  expect(screen.queryByText("Mood tags:")).toBeNull();
  expect(document.querySelector(".stage-strip")!.querySelectorAll("button")).toHaveLength(4);
});

it("starts the box at the top when another film comes on stage", () => {
  const { rerender } = render(<StagePanel movie={film} world={world} why="x" />);
  const before = document.querySelector(".stage-info__body");
  rerender(<StagePanel movie={{ ...film, id: "other" }} world={world} why="x" />);
  expect(document.querySelector(".stage-info__body")).not.toBe(before);
});

it("lets keyboard users focus and scroll the box text", () => {
  render(<StagePanel movie={film} world={world} why="x" />);
  const region = screen.getByRole("region", { name: `About ${film.title}` });
  expect(region).toHaveClass("stage-info__body");
  expect(region).toHaveAttribute("tabindex", "0");
});
