"use client";

import { useId, useState } from "react";
import { Info } from "lucide-react";
import { Floating } from "./Floating";

interface Props {
  text: string;
  className?: string;
}

/**
 * Small inline tooltip used throughout the app to surface methodological
 * choices transparently (e.g. "why lineage and not a single institution ID?",
 * "what is a core publication?", "full vs fractional counting").
 *
 * Opens on hover, keyboard focus or click; positioned by <Floating> so the
 * bubble always stays inside the window (flipped / shifted near edges,
 * sticky header included).
 */
export function InfoTooltip({ text, className = "" }: Props) {
  const [hover, setHover] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [anchor, setAnchor] = useState<HTMLButtonElement | null>(null);
  const id = useId();
  const open = hover || pinned;

  return (
    <span className={`inline-flex items-center ${className}`}>
      <button
        ref={setAnchor}
        type="button"
        onClick={() => setPinned((v) => !v)}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onFocus={() => setHover(true)}
        onBlur={() => {
          setHover(false);
          setPinned(false);
        }}
        onKeyDown={(e) => e.key === "Escape" && (setHover(false), setPinned(false))}
        className="text-gray-400 hover:text-gray-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded"
        aria-label="Information méthodologique"
        aria-describedby={open ? id : undefined}
      >
        <Info size={14} />
      </button>
      <Floating
        anchor={anchor}
        open={open}
        id={id}
        role="tooltip"
        className="w-72 bg-gray-800 text-white text-xs font-normal normal-case tracking-normal text-left rounded px-3 py-2 shadow-lg leading-relaxed whitespace-normal"
      >
        {text}
      </Floating>
    </span>
  );
}
