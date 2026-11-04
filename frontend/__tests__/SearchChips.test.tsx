import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import SearchChips from "@/components/search/SearchChips";
import { emptyCriteria, type Criteria } from "@/lib/searchState";

const tags = [
  { idx: 0, tag: "dark" },
  { idx: 1, tag: "space travel" },
  { idx: 2, tag: "horror" },
  { idx: 3, tag: "medieval" },
];

function setup(criteria: Partial<Criteria> = {}, hidden = 0) {
  const onChange = vi.fn();
  render(<SearchChips tags={tags} criteria={{ ...emptyCriteria(), ...criteria }} onChange={onChange} hiddenCount={hidden} />);
  return onChange;
}

it("mode switch shows all three modes, marks the current one and sets the chosen one", async () => {
  const onChange = setup({ tags: [{ idx: 1, weight: 6, mode: "prefer" }] });
  const group = screen.getByRole("group", { name: "Mode for space travel" });
  expect(within(group).getByRole("button", { name: "Prefer" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(within(group).getByRole("button", { name: "Must" }));
  expect(onChange.mock.calls[0][0].tags[0].mode).toBe("must");
  await userEvent.click(within(group).getByRole("button", { name: "Exclude" }));
  expect(onChange.mock.calls[1][0].tags[0].mode).toBe("not");
});

it("an excluded tag can be switched back to prefer", async () => {
  const onChange = setup({ tags: [{ idx: 2, weight: 6, mode: "not" }] });
  const group = screen.getByRole("group", { name: "Mode for horror" });
  await userEvent.click(within(group).getByRole("button", { name: "Prefer" }));
  expect(onChange.mock.calls[0][0].tags[0].mode).toBe("prefer");
});

it("weight stars are labelled and set the weight", async () => {
  const onChange = setup({ tags: [{ idx: 0, weight: 4, mode: "prefer" }] });
  expect(screen.getByText("Weight")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Weight 5 of 5 for dark" }));
  expect(onChange.mock.calls[0][0].tags[0].weight).toBe(10);
});

it("excluded chips render with the excluded style and the hidden count shows", () => {
  setup({ tags: [{ idx: 2, weight: 5, mode: "not" }], exclude_genres: ["Horror"] }, 214);
  const chip = screen.getByText("horror").closest(".chip")!;
  expect(chip).toHaveClass("chip--excluded");
  expect(screen.getByText("🚫 Horror (genre)")).toBeInTheDocument();
  expect(screen.getByText("→ 214 films hidden")).toBeInTheDocument();
});

it("+ Tag adds a chip from the picker", async () => {
  const onChange = setup();
  await userEvent.click(screen.getByRole("button", { name: "+ Tag" }));
  await userEvent.type(screen.getByRole("searchbox", { name: "Find a mood tag" }), "medi");
  await userEvent.click(screen.getByRole("button", { name: "medieval" }));
  expect(onChange.mock.calls.at(-1)![0].tags).toEqual([{ idx: 3, weight: 6, mode: "prefer" }]);
});

it("× removes a chip; person and filter chips are removable", () => {
  const onChange = setup({ tags: [{ idx: 0, weight: 6, mode: "prefer" }], person: "Sandra Hüller", max_runtime_min: 120 });
  fireEvent.click(screen.getByRole("button", { name: "Remove dark" }));
  expect(onChange.mock.calls[0][0].tags).toEqual([]);
  fireEvent.click(screen.getByRole("button", { name: "Remove person Sandra Hüller" }));
  expect(onChange.mock.calls[1][0].person).toBeNull();
  expect(screen.getByText("< 120 min")).toBeInTheDocument();
});

it("the tag picker tolerates typos", async () => {
  const onChange = setup();
  await userEvent.click(screen.getByRole("button", { name: "+ Tag" }));
  await userEvent.type(screen.getByRole("searchbox", { name: "Find a mood tag" }), "medival");
  await userEvent.click(screen.getByRole("button", { name: "medieval" }));
  expect(onChange.mock.calls.at(-1)![0].tags).toEqual([{ idx: 3, weight: 6, mode: "prefer" }]);
});

it("the tag picker says so when nothing fits", async () => {
  setup();
  await userEvent.click(screen.getByRole("button", { name: "+ Tag" }));
  await userEvent.type(screen.getByRole("searchbox", { name: "Find a mood tag" }), "zzzz");
  expect(screen.getByText("No mood tag like that")).toBeInTheDocument();
});

it("each exclusion says what it hides in this search, and when it hides nothing", () => {
  render(
    <SearchChips
      tags={tags}
      criteria={{ ...emptyCriteria(), tags: [{ idx: 0, weight: 6, mode: "not" }], exclude_genres: ["Horror", "Western"] }}
      onChange={() => {}}
      hiddenBy={{ "tag:0": 3, "genre:Horror": 0, "genre:Western": 1 }}
    />,
  );
  expect(screen.getByText("hides 3 films here")).toBeInTheDocument();
  expect(screen.getByText("hides 1 film here")).toBeInTheDocument();
  expect(screen.getByText("none of these films are Horror: changes nothing")).toBeInTheDocument();
});

it("an exclusion without a count shows no note", () => {
  render(<SearchChips tags={tags} criteria={{ ...emptyCriteria(), exclude_genres: ["Horror"] }} onChange={() => {}} />);
  expect(screen.queryByText(/changes nothing|hides/)).toBeNull();
});
