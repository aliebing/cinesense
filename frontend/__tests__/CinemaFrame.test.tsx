import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import CinemaFrame from "@/components/cinema/CinemaFrame";

it("renders children inside a cinemascope stage with curtains and letterbox bars", () => {
  render(
    <CinemaFrame>
      <p>Inhalt</p>
    </CinemaFrame>,
  );
  const stage = screen.getByTestId("cinema-stage");
  expect(stage).toContainElement(screen.getByText("Inhalt"));
  expect(screen.getAllByTestId("curtain")).toHaveLength(2);
  expect(screen.getAllByTestId("letterbox")).toHaveLength(2);
});
