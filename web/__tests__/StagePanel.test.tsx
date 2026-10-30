import { render, screen } from "@testing-library/react";
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

it("shows streaming providers, TMDB rating, badge and why text", () => {
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
  const names = ["👍 More like this", "⚡ More action", "😂 Funnier", "👎 Not for me"];
  for (const name of names) expect(screen.getByRole("button", { name })).toBeDisabled();
});


it("streaming states: unknown, not in Germany, and rent/buy collapsed", () => {
  const { rerender } = render(<StagePanel movie={{ ...base, availability: { in_cinema_de: false, streaming_de: null, subscription_services: [] } }} world={world} why="x" />);
  expect(screen.getByText("Streaming availability unknown")).toBeInTheDocument();
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

it("links each offer to the provider, once per service, and offers a search when nothing is known", () => {
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

it("shows the plot, folded to a few lines until opened", async () => {
  render(<StagePanel movie={{ ...base, overview: "Raoul and his wife Solange are eating in a restaurant." }} world={world} why="x" />);
  expect(screen.getByText(/Raoul and his wife Solange/)).toBeInTheDocument();
  const more = screen.getByRole("button", { name: "More" });
  await userEvent.click(more);
  expect(more).toHaveAttribute("aria-expanded", "true");
  expect(more).toHaveTextContent("Less");
});

it("links to IMDb and Wikipedia and shows people, tags and German cinema release", () => {
  render(
    <StagePanel
      movie={{ ...base, imdb_id: "tt0816692", wikipedia_title: "Interstellar (film)", directors: ["Christopher Nolan"], cast_top: ["Matthew McConaughey"], top_tags: ["space travel"], release_date_de: "2026-10-01", availability: { in_cinema_de: true, streaming_de: null, subscription_services: [] } }}
      world={world}
      why="x"
    />,
  );
  expect(screen.getByRole("link", { name: "IMDb" })).toHaveAttribute("href", "https://www.imdb.com/title/tt0816692/");
  expect(screen.getByRole("link", { name: "Wikipedia" })).toHaveAttribute("href", "https://en.wikipedia.org/wiki/Interstellar_(film)");
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
