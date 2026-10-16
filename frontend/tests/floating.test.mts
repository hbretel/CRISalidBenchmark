/**
 * Readability test of floating elements: whatever the trigger position
 * (corners, edges, under a sticky header, partly scrolled out) and the
 * content size (up to larger than the window), the placed element must lie
 * entirely inside the visible window. Run with `npm test`.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { computeFloatingPosition, isInsideViewport, VIEWPORT_MARGIN, type Placement } from "../src/lib/floating.ts";

const VIEWPORTS = [
  { width: 1440, height: 900 },
  { width: 1024, height: 700 },
  { width: 375, height: 667 }, // phone
  { width: 260, height: 180 }, // smaller than most bubbles
];
const SIZES = [
  { width: 288, height: 60 }, // InfoTooltip (w-72), short text
  { width: 288, height: 260 }, // InfoTooltip, long methodological note
  { width: 420, height: 520 }, // score breakdown popover
  { width: 2000, height: 2000 }, // larger than any window
];
const PLACEMENTS: Placement[] = ["top", "bottom", "left", "right"];
const TRIGGER = { width: 14, height: 14 };

function triggerPositions(viewport: { width: number; height: number }) {
  const xs = [0, 4, viewport.width / 2, viewport.width - 18, viewport.width - TRIGGER.width];
  const ys = [0, 4, 30, viewport.height / 2, viewport.height - 18, viewport.height - TRIGGER.height];
  return xs.flatMap((left) => ys.map((top) => ({ top, left, ...TRIGGER })));
}

test("floating elements always stay inside the window", () => {
  let cases = 0;
  for (const viewport of VIEWPORTS) {
    for (const size of SIZES) {
      for (const preferred of PLACEMENTS) {
        for (const trigger of triggerPositions(viewport)) {
          const pos = computeFloatingPosition(trigger, size, viewport, preferred);
          const placed = {
            top: pos.top,
            left: pos.left,
            width: Math.min(size.width, pos.maxWidth),
            height: Math.min(size.height, pos.maxHeight),
          };
          assert.ok(
            isInsideViewport(placed, viewport, VIEWPORT_MARGIN),
            `outside: ${JSON.stringify({ viewport, size, preferred, trigger, placed })}`,
          );
          cases++;
        }
      }
    }
  }
  assert.ok(cases > 1000);
});

test("tooltip flips below a trigger at the top of the window (sticky header)", () => {
  const pos = computeFloatingPosition({ top: 20, left: 600, width: 14, height: 14 }, { width: 288, height: 90 }, { width: 1440, height: 900 });
  assert.equal(pos.placement, "bottom");
  assert.ok(pos.top >= 20 + 14);
});

test("tooltip keeps its preferred side when there is room", () => {
  const pos = computeFloatingPosition({ top: 500, left: 600, width: 14, height: 14 }, { width: 288, height: 90 }, { width: 1440, height: 900 });
  assert.equal(pos.placement, "top");
  assert.ok(pos.top + 90 <= 500);
});

test("tooltip near the right edge is shifted left, not cut", () => {
  const viewport = { width: 1024, height: 700 };
  const pos = computeFloatingPosition({ top: 400, left: 1010, width: 14, height: 14 }, { width: 288, height: 90 }, viewport);
  assert.equal(pos.left + 288, viewport.width - VIEWPORT_MARGIN);
});
