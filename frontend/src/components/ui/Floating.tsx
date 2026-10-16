"use client";

import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { computeFloatingPosition, isInsideViewport, VIEWPORT_MARGIN, type Placement } from "@/lib/floating";

interface Props {
  /** Element the floating content is attached to. */
  anchor: HTMLElement | null;
  open: boolean;
  preferred?: Placement;
  className?: string;
  role?: string;
  id?: string;
  children: React.ReactNode;
}

/**
 * Single entry point for every floating element of the app (tooltips,
 * popovers, context menus): rendered in a portal on <body> with
 * `position: fixed`, so no ancestor `overflow` can clip it, and placed by
 * lib/floating.ts so it never leaves the visible window — re-placed on
 * scroll (any scroll container) and resize. Its size is capped to the window;
 * longer content scrolls inside.
 *
 * In development, a placement that still ends up outside the window is
 * reported in the console (readability check for future elements, together
 * with tests/floating.test.mts and tests/floating-usage.test.mts).
 */
export function Floating({ anchor, open, preferred = "top", className = "", role, id, children }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<React.CSSProperties>({ visibility: "hidden", top: 0, left: 0 });

  const place = useCallback(() => {
    const el = ref.current;
    if (!el || !anchor) return;
    const viewport = { width: window.innerWidth, height: window.innerHeight };
    // Measure the natural size with the caps that will apply.
    el.style.maxWidth = `${viewport.width - 2 * VIEWPORT_MARGIN}px`;
    el.style.maxHeight = `${viewport.height - 2 * VIEWPORT_MARGIN}px`;
    const size = { width: el.offsetWidth, height: el.offsetHeight };
    const trigger = anchor.getBoundingClientRect();
    const pos = computeFloatingPosition(trigger, size, viewport, preferred);
    setStyle({ top: pos.top, left: pos.left, maxWidth: pos.maxWidth, maxHeight: pos.maxHeight });
    if (process.env.NODE_ENV !== "production") {
      const placed = { top: pos.top, left: pos.left, width: Math.min(size.width, pos.maxWidth), height: Math.min(size.height, pos.maxHeight) };
      if (!isInsideViewport(placed, viewport)) {
        console.error("[Floating] élément flottant hors de la fenêtre visible", { placed, viewport });
      }
    }
  }, [anchor, preferred]);

  useLayoutEffect(() => {
    if (!open) return;
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open, place, children]);

  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div
      ref={ref}
      id={id}
      role={role}
      data-floating=""
      style={{ position: "fixed", zIndex: 60, overflow: "auto", ...style }}
      className={className}
    >
      {children}
    </div>,
    document.body,
  );
}
