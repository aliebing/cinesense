import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import AdvancedSearch from "@/components/search/AdvancedSearch";
import { emptyCriteria } from "@/lib/searchState";

it("submits title, person with role, years, kind and extended", async () => {
  const onSubmit = vi.fn();
  render(<AdvancedSearch criteria={emptyCriteria()} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText("Title"), "interstelar");
  await userEvent.type(screen.getByLabelText("Actor or director"), "Sandra Hueller");
  await userEvent.click(within(screen.getByRole("group", { name: "Role" })).getByRole("button", { name: "Actor" }));
  await userEvent.type(screen.getByLabelText("From year"), "2010");
  await userEvent.click(within(screen.getByRole("group", { name: "Kind" })).getByRole("button", { name: "Documentaries" }));
  await userEvent.click(screen.getByLabelText(/Extended search/));
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  const c = onSubmit.mock.calls[0][0];
  expect(c).toMatchObject({ title: "interstelar", person: "Sandra Hueller", person_role: "cast", year_from: 2010, kind: "documentary", extended: true });
});

it("shows role and kind as switches with the current choice highlighted", async () => {
  render(<AdvancedSearch criteria={{ ...emptyCriteria(), person_role: "director", kind: "film" }} onSubmit={() => {}} />);
  const role = within(screen.getByRole("group", { name: "Role" }));
  expect(role.getByRole("button", { name: "Director" })).toHaveAttribute("aria-pressed", "true");
  expect(role.getByRole("button", { name: "Any" })).toHaveAttribute("aria-pressed", "false");
  const kind = within(screen.getByRole("group", { name: "Kind" }));
  expect(kind.getByRole("button", { name: "Feature films" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(kind.getByRole("button", { name: "All" }));
  expect(kind.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
});
