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

const suggest = vi.fn();
vi.mock("@/lib/api", () => ({ suggest: (...a: unknown[]) => suggest(...a) }));

it("suggests titles from the 4th letter and takes one only when it is clicked", async () => {
  suggest.mockResolvedValue({ ok: true, data: [{ value: "The Matrix", label: "The Matrix (1999)" }] });
  const onSubmit = vi.fn();
  render(<AdvancedSearch criteria={emptyCriteria()} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText("Title"), "mat");
  expect(screen.queryByRole("option")).toBeNull(); // three letters: no suggestions yet
  await userEvent.type(screen.getByLabelText("Title"), "r");
  await userEvent.click(await screen.findByRole("option", { name: "The Matrix (1999)" }));
  expect(screen.getByLabelText("Title")).toHaveValue("The Matrix");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(onSubmit.mock.calls[0][0]).toMatchObject({ title: "The Matrix" });
  expect(suggest).toHaveBeenCalledWith("title", "matr");
});

it("does not search with typed text that was not picked from the suggestions", async () => {
  suggest.mockResolvedValue({ ok: true, data: [{ value: "Sandra Bullock", label: "Sandra Bullock" }] });
  const onSubmit = vi.fn();
  render(<AdvancedSearch criteria={emptyCriteria()} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText("Actor or director"), "bullok");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(onSubmit).not.toHaveBeenCalled();
  expect(screen.getByText("Pick a name from the suggestions")).toBeInTheDocument();
});

it("extended search may use typed text (newer films are not in the suggestions)", async () => {
  suggest.mockResolvedValue({ ok: true, data: [] });
  const onSubmit = vi.fn();
  render(<AdvancedSearch criteria={emptyCriteria()} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText("Title"), "Some new film");
  await userEvent.click(screen.getByLabelText(/Extended search/));
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(onSubmit.mock.calls[0][0]).toMatchObject({ title: "Some new film", extended: true });
});

it("a year that is not a real four-digit year is pointed out, not silently ignored", async () => {
  const onSubmit = vi.fn();
  render(<AdvancedSearch criteria={emptyCriteria()} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText("From year"), "199");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(onSubmit).not.toHaveBeenCalled();
  expect(screen.getByText("Enter years as four digits, e.g. 1994")).toBeInTheDocument();
  expect(screen.getByLabelText("From year")).toHaveAttribute("aria-invalid", "true");
});

it("a year range that runs backwards is pointed out", async () => {
  const onSubmit = vi.fn();
  render(<AdvancedSearch criteria={emptyCriteria()} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText("From year"), "2010");
  await userEvent.type(screen.getByLabelText("To year"), "1990");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(onSubmit).not.toHaveBeenCalled();
  expect(screen.getByText("'From year' is after 'To year'")).toBeInTheDocument();
});

it("years before films existed or far in the future are pointed out", async () => {
  const onSubmit = vi.fn();
  render(<AdvancedSearch criteria={emptyCriteria()} onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText("To year"), "3024");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(onSubmit).not.toHaveBeenCalled();
  expect(screen.getByText(/between 1888 and/)).toBeInTheDocument();
});
