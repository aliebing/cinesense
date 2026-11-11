import { fireEvent, render } from "@testing-library/react";
import { useRef } from "react";
import { describe, expect, it, vi } from "vitest";
import { useForwardScroll } from "@/lib/useForwardScroll";

function Page() {
  const ref = useRef<HTMLDivElement>(null);
  useForwardScroll(ref);
  return (
    <div>
      <div data-testid="curtain" />
      <div data-testid="list" ref={ref}>
        <p data-testid="film">film</p>
      </div>
    </div>
  );
}

function setup() {
  const view = render(<Page />);
  const list = view.getByTestId("list");
  const scrollBy = vi.fn();
  list.scrollBy = scrollBy as unknown as typeof list.scrollBy;
  Object.defineProperty(list, "clientHeight", { value: 1000 });
  return { ...view, scrollBy };
}

describe("useForwardScroll", () => {
  it("scrolls the results when the wheel turns over the curtains or the room around the screen", () => {
    const { getByTestId, scrollBy } = setup();
    fireEvent.wheel(getByTestId("curtain"), { deltaY: 120 });
    expect(scrollBy).toHaveBeenCalledWith({ top: 120 });
  });

  it("leaves a wheel over the results to the browser, and counts wheel lines as pixels", () => {
    const { getByTestId, scrollBy } = setup();
    fireEvent.wheel(getByTestId("film"), { deltaY: 120 });
    expect(scrollBy).not.toHaveBeenCalled();
    fireEvent.wheel(getByTestId("curtain"), { deltaY: 3, deltaMode: 1 });
    expect(scrollBy).toHaveBeenCalledWith({ top: 120 });
  });

  it("pages with the keys while nothing has focus, but never steals them from a field", () => {
    const { scrollBy, container } = setup();
    fireEvent.keyDown(document.body, { key: "PageDown" });
    expect(scrollBy).toHaveBeenLastCalledWith({ top: 900 });
    fireEvent.keyDown(document.body, { key: " ", shiftKey: true });
    expect(scrollBy).toHaveBeenLastCalledWith({ top: -900 });
    const input = document.createElement("input");
    container.appendChild(input);
    input.focus();
    scrollBy.mockClear();
    fireEvent.keyDown(input, { key: " " });
    expect(scrollBy).not.toHaveBeenCalled();
  });
});
