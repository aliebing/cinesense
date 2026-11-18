import { afterEach, expect, it, vi } from "vitest";
import { attachTouchDrag, glideDistance } from "@/lib/touchDrag";

/** jsdom has no PointerEvent: a plain event with the fields the helper reads */
function pointer(el: Element, type: string, x: number, y: number, t: number, pointerType = "touch") {
  const e = new Event(type, { bubbles: true, cancelable: true });
  Object.defineProperties(e, {
    pointerId: { value: 1 },
    pointerType: { value: pointerType },
    clientX: { value: x },
    clientY: { value: y },
    timeStamp: { value: t },
  });
  el.dispatchEvent(e);
}

function click(el: Element, t: number) {
  const e = new MouseEvent("click", { bubbles: true, cancelable: true });
  Object.defineProperty(e, "timeStamp", { value: t });
  el.dispatchEvent(e);
  return e;
}

function setup() {
  const row = document.createElement("div");
  const tile = document.createElement("button");
  row.appendChild(tile);
  document.body.appendChild(row);
  const onStart = vi.fn();
  const onDrag = vi.fn();
  const onEnd = vi.fn();
  const detach = attachTouchDrag(row, { onStart, onDrag, onEnd });
  return { row, tile, onStart, onDrag, onEnd, detach };
}

afterEach(() => {
  document.body.innerHTML = "";
});

it("drags the row with a sideways finger and reports the flick", () => {
  const { tile, onStart, onDrag, onEnd } = setup();
  pointer(tile, "pointerdown", 200, 100, 0);
  pointer(tile, "pointermove", 180, 102, 16);
  pointer(tile, "pointermove", 150, 103, 32);
  pointer(tile, "pointerup", 150, 103, 40);
  expect(onStart).toHaveBeenCalledWith(tile);
  expect(onDrag.mock.calls.map((c) => c[0])).toEqual([-20, -30]);
  expect(onEnd).toHaveBeenCalledTimes(1);
  expect(onEnd.mock.calls[0][0]).toBeLessThan(0);
});

it("leaves a tap a click, and swallows the click that ends a swipe", () => {
  const { tile, onDrag } = setup();
  const select = vi.fn();
  tile.addEventListener("click", select);
  pointer(tile, "pointerdown", 200, 100, 0);
  pointer(tile, "pointermove", 203, 101, 10);
  pointer(tile, "pointerup", 203, 101, 20);
  click(tile, 25);
  expect(onDrag).not.toHaveBeenCalled();
  expect(select).toHaveBeenCalledTimes(1);

  pointer(tile, "pointerdown", 200, 100, 1000);
  pointer(tile, "pointermove", 140, 100, 1020);
  pointer(tile, "pointerup", 140, 100, 1030);
  const swallowed = click(tile, 1035);
  expect(swallowed.defaultPrevented).toBe(true);
  expect(select).toHaveBeenCalledTimes(1);
  click(tile, 2000); // a later tap opens again
  expect(select).toHaveBeenCalledTimes(2);
});

it("leaves upright swipes to the page and ignores the mouse", () => {
  const { tile, onDrag, onStart } = setup();
  pointer(tile, "pointerdown", 200, 100, 0);
  pointer(tile, "pointermove", 210, 160, 16);
  pointer(tile, "pointerup", 210, 160, 30);
  pointer(tile, "pointerdown", 200, 100, 100, "mouse");
  pointer(tile, "pointermove", 100, 100, 116, "mouse");
  expect(onStart).not.toHaveBeenCalled();
  expect(onDrag).not.toHaveBeenCalled();
});

it("does not fling when the finger rested before lifting", () => {
  const { tile, onEnd } = setup();
  pointer(tile, "pointerdown", 200, 100, 0);
  pointer(tile, "pointermove", 150, 100, 16);
  pointer(tile, "pointerup", 150, 100, 400);
  expect(onEnd).toHaveBeenCalledWith(0);
  expect(glideDistance(1000)).toBeGreaterThan(0);
});

it("stops listening once detached", () => {
  const { tile, onDrag, detach } = setup();
  detach();
  pointer(tile, "pointerdown", 200, 100, 0);
  pointer(tile, "pointermove", 100, 100, 16);
  expect(onDrag).not.toHaveBeenCalled();
});
