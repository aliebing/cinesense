import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import ImpressumPage from "@/app/impressum/page";
import DatenschutzPage from "@/app/datenschutz/page";
import { datenschutz } from "@/lib/legal/datenschutz";

it("every cinema frame links Impressum and privacy notice", () => {
  render(<CinemaFrame>x</CinemaFrame>);
  expect(screen.getByRole("link", { name: "Impressum" })).toHaveAttribute("href", "/impressum");
  expect(screen.getByRole("link", { name: "Datenschutz" })).toHaveAttribute("href", "/datenschutz");
});

it("Impressum names provider and address, German first, English on request", () => {
  render(<ImpressumPage />);
  expect(screen.getByRole("heading", { level: 1, name: "Impressum" })).toBeInTheDocument();
  expect(screen.getByText("Panoramaweg 6")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "aliebing@gmx.de" })).toHaveAttribute("href", "mailto:aliebing@gmx.de");
  fireEvent.click(screen.getByRole("button", { name: "English version" }));
  expect(screen.getByRole("heading", { level: 1, name: "Legal notice" })).toBeInTheDocument();
});

it("privacy notice names what CineSense actually uses", () => {
  render(<DatenschutzPage />);
  expect(screen.getByRole("heading", { level: 1, name: "Datenschutzerklärung" })).toBeInTheDocument();
  const text = JSON.stringify(datenschutz("de"));
  for (const s of ["cinesense.user", "youtube-nocookie.com", "OpenRouter", "Movie of the Night", "nur im Arbeitsspeicher"]) expect(text).toContain(s);
  expect(datenschutz("en").sections.length).toBe(datenschutz("de").sections.length);
});
