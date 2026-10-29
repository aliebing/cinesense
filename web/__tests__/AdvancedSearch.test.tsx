import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import AdvancedSearch from "@/components/search/AdvancedSearch";
import { emptyCriteria } from "@/lib/searchState";

it("submits title, person with role, years, kind and extended", async () => {
  const onSubmit = vi.fn();
  render(<AdvancedSearch criteria={emptyCriteria()} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText("Title"), "interstelar");
  await userEvent.type(screen.getByLabelText("Actor or director"), "Sandra Hueller");
  await userEvent.selectOptions(screen.getByLabelText("Role"), "cast");
  await userEvent.type(screen.getByLabelText("From year"), "2010");
  await userEvent.selectOptions(screen.getByLabelText("Kind"), "documentary");
  await userEvent.click(screen.getByLabelText(/Extended search/));
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  const c = onSubmit.mock.calls[0][0];
  expect(c).toMatchObject({ title: "interstelar", person: "Sandra Hueller", person_role: "cast", year_from: 2010, kind: "documentary", extended: true });
});
