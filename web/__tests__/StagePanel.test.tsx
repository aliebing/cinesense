import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import StagePanel from "@/components/genre/StagePanel";
import { sampleMovies, sampleWorlds } from "./fixtures";

const base = sampleMovies(1)[0];
const world = sampleWorlds[1];

it("shows a note instead of an iframe when there is no trailer", () => {
  render(<StagePanel movie={{ ...base, youtube_key: null }} world={world} why="Test" />);
  expect(screen.getByText("Kein offizieller Trailer verfügbar")).toBeInTheDocument();
  expect(screen.queryByTitle(/Offizieller Trailer/)).toBeNull();
});

it("loads the youtube-nocookie embed only after clicking play", async () => {
  render(<StagePanel movie={{ ...base, youtube_key: "abc123" }} world={world} why="Test" />);
  expect(screen.queryByTitle(/Offizieller Trailer/)).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: /Trailer abspielen/ }));
  const iframe = screen.getByTitle("Offizieller Trailer: Demo-Film 01");
  expect(iframe.getAttribute("src")).toContain("youtube-nocookie.com/embed/abc123");
});

it("labels the placeholder trailer", () => {
  render(<StagePanel movie={{ ...base, youtube_key: "placeholder" }} world={world} why="Test" />);
  expect(screen.getByText("Platzhalter-Trailer")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Trailer abspielen/ })).toBeNull();
});

it("shows streaming providers, German-formatted TMDB rating, badge and why text", () => {
  const movie = {
    ...base,
    vote_average: 7.56,
    availability: { in_cinema_de: false, streaming_flatrate_de: ["Netflix", "Disney+"] },
  };
  render(<StagePanel movie={movie} world={world} why="Gut bewertet" />);
  expect(screen.getByText("📺 Im Stream bei Netflix, Disney+")).toBeInTheDocument();
  expect(screen.getByText("⭐ TMDB 7,6")).toBeInTheDocument();
  expect(screen.getByText("Platzhalter")).toBeInTheDocument();
  expect(screen.getByText("Gut bewertet")).toBeInTheDocument();
  expect(screen.queryByText("🎬 Im Kino")).toBeNull();
});

it("renders the four feedback buttons disabled", () => {
  render(<StagePanel movie={base} world={world} why="Test" />);
  const names = ["👍 Mehr davon", "⚡ Mehr Action", "😂 Lustiger", "👎 Nicht mein Ding"];
  for (const name of names) expect(screen.getByRole("button", { name })).toBeDisabled();
});
