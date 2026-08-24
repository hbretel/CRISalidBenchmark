"use client";

import { useRef, useState } from "react";
import { Info } from "lucide-react";

interface Props {
  text: string;
  className?: string;
}

/**
 * Small inline tooltip used throughout the app to surface methodological
 * choices transparently (e.g. "why lineage and not a single institution ID?",
 * "what is a core publication?", "full vs fractional counting").
 *
 * Placement is measured on open rather than fixed above the trigger: near the
 * top of the viewport (e.g. inside the sticky dashboard header) a bubble
 * anchored above the icon gets clipped by the page top — so we flip it below
 * whenever there isn't enough room above.
 */
export function InfoTooltip({ text, className = "" }: Props) {
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState<"top" | "bottom">("top");
  const buttonRef = useRef<HTMLButtonElement>(null);

  function handleOpen() {
    const rect = buttonRef.current?.getBoundingClientRect();
    const BUBBLE_HEIGHT = 90; // rough max height incl. margin, enough for the flip decision
    setPlacement(rect && rect.top < BUBBLE_HEIGHT ? "bottom" : "top");
    setOpen((v) => !v);
  }

  return (
    <span className={`relative inline-flex items-center ${className}`}>
      <button
        ref={buttonRef}
        type="button"
        onClick={handleOpen}
        onBlur={() => setOpen(false)}
        className="text-gray-400 hover:text-gray-600 focus:outline-none"
        aria-label="Information méthodologique"
      >
        <Info size={14} />
      </button>
      {open && (
        <span
          className={`absolute z-50 left-1/2 -translate-x-1/2 w-72 bg-gray-800 text-white text-xs rounded px-3 py-2 shadow-lg leading-relaxed ${
            placement === "top" ? "bottom-full mb-2" : "top-full mt-2"
          }`}
        >
          {text}
        </span>
      )}
    </span>
  );
}
