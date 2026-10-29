import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
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
    vote_average: 7.56,
    availability: { in_cinema_de: false, streaming_flatrate_de: ["Netflix", "Disney+"] },
  };
  render(<StagePanel movie={movie} world={world} why="Highly rated" />);
  expect(screen.getByText("📺 Streaming on Netflix, Disney+")).toBeInTheDocument();
  expect(screen.getByText("⭐ TMDB 7.6")).toBeInTheDocument();
  expect(screen.getByText("Placeholder")).toBeInTheDocument();
  expect(screen.getByText("Highly rated")).toBeInTheDocument();
  expect(screen.queryByText("🎬 In cinemas")).toBeNull();
});

it("renders the four feedback buttons disabled", () => {
  render(<StagePanel movie={base} world={world} why="Test" />);
  const names = ["👍 More like this", "⚡ More action", "😂 Funnier", "👎 Not for me"];
  for (const name of names) expect(screen.getByRole("button", { name })).toBeDisabled();
});
