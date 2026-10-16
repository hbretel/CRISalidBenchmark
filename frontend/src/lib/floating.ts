/**
 * Placement of floating elements (tooltips, popovers, context menus) so they
 * always stay inside the visible window.
 *
 * Pure function, no DOM access — unit-tested in tests/floating.test.mts for
 * every trigger position (corners, edges, sticky header, tiny viewports).
 * Every floating element of the app must be positioned through it (via
 * components/ui/Floating.tsx); tests/floating-usage.test.mts enforces that for
 * future components too.
 *
 * Strategy: preferred side (top), flipped to the opposite side when it does
 * not fit, then to whichever side has the most room; the cross axis is
 * centred on the trigger and clamped into the viewport; the element is
 * finally clamped on both axes, and its maximum size is capped to the
 * viewport (minus margins) so even content larger than the window stays
 * readable (it scrolls inside instead of overflowing).
 */

export type Placement = "top" | "bottom" | "left" | "right";

export interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface FloatingPosition {
  top: number;
  left: number;
  placement: Placement;
  maxWidth: number;
  maxHeight: number;
}

export const VIEWPORT_MARGIN = 8;
export const TRIGGER_GAP = 6;

const OPPOSITE: Record<Placement, Placement> = { top: "bottom", bottom: "top", left: "right", right: "left" };

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), Math.max(min, max));
}

/** Room available on each side of the trigger, margins and gap excluded. */
function room(trigger: Rect, viewport: Size): Record<Placement, number> {
  return {
    top: trigger.top - TRIGGER_GAP - VIEWPORT_MARGIN,
    bottom: viewport.height - (trigger.top + trigger.height) - TRIGGER_GAP - VIEWPORT_MARGIN,
    left: trigger.left - TRIGGER_GAP - VIEWPORT_MARGIN,
    right: viewport.width - (trigger.left + trigger.width) - TRIGGER_GAP - VIEWPORT_MARGIN,
  };
}

function fits(placement: Placement, size: Size, space: Record<Placement, number>): boolean {
  const needed = placement === "top" || placement === "bottom" ? size.height : size.width;
  return space[placement] >= needed;
}

export function computeFloatingPosition(
  trigger: Rect,
  floating: Size,
  viewport: Size,
  preferred: Placement = "top",
): FloatingPosition {
  const space = room(trigger, viewport);
  const maxWidth = Math.max(0, viewport.width - 2 * VIEWPORT_MARGIN);
  const maxHeight = Math.max(0, viewport.height - 2 * VIEWPORT_MARGIN);
  const size: Size = { width: Math.min(floating.width, maxWidth), height: Math.min(floating.height, maxHeight) };

  let placement = preferred;
  if (!fits(placement, size, space)) {
    const candidates: Placement[] = [OPPOSITE[preferred], "top", "bottom", "right", "left"];
    placement =
      candidates.find((p) => fits(p, size, space)) ??
      candidates.reduce((best, p) => (space[p] > space[best] ? p : best), preferred);
  }

  let top: number;
  let left: number;
  if (placement === "top" || placement === "bottom") {
    top = placement === "top" ? trigger.top - TRIGGER_GAP - size.height : trigger.top + trigger.height + TRIGGER_GAP;
    left = trigger.left + trigger.width / 2 - size.width / 2;
  } else {
    left = placement === "left" ? trigger.left - TRIGGER_GAP - size.width : trigger.left + trigger.width + TRIGGER_GAP;
    top = trigger.top + trigger.height / 2 - size.height / 2;
  }

  return {
    top: clamp(top, VIEWPORT_MARGIN, viewport.height - VIEWPORT_MARGIN - size.height),
    left: clamp(left, VIEWPORT_MARGIN, viewport.width - VIEWPORT_MARGIN - size.width),
    placement,
    maxWidth,
    maxHeight,
  };
}

/** True if `rect` lies entirely inside the viewport (margins included). */
export function isInsideViewport(rect: Rect, viewport: Size, margin = 0): boolean {
  return (
    rect.left >= margin - 0.5 &&
    rect.top >= margin - 0.5 &&
    rect.left + rect.width <= viewport.width - margin + 0.5 &&
    rect.top + rect.height <= viewport.height - margin + 0.5
  );
}
