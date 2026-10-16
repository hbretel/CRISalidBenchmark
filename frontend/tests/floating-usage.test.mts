/**
 * Guard for future components: every floating element (tooltip, popover,
 * context menu) must go through components/ui/Floating.tsx, the only place
 * whose placement is tested to stay inside the window (tests/floating.test.mts).
 * Hand-rolled bubbles (`absolute`/`fixed` + z-index), ad-hoc portals and
 * Recharts tooltips allowed to escape their chart are rejected.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const SRC = join(import.meta.dirname, "..", "src");
// Allowed: the floating primitive itself, and the modal shell (full-window
// overlay, centred, scrollable — cannot overflow).
const ALLOWED = new Set(["components/ui/Floating.tsx", "components/ui/Modal.tsx"]);

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : /\.(tsx|ts)$/.test(name) ? [path] : [];
  });
}

const RULES: { name: string; pattern: RegExp }[] = [
  { name: "absolute/fixed element with a z-index (hand-rolled popover)", pattern: /className=[^>]*\b(absolute|fixed)\b[^"'`]*\bz-\d+/ },
  { name: "z-index then absolute/fixed (hand-rolled popover)", pattern: /className=[^>]*\bz-\d+[^"'`]*\b(absolute|fixed)\b/ },
  { name: "createPortal outside <Floating>", pattern: /createPortal\s*\(/ },
  { name: "Recharts tooltip allowed to leave its chart", pattern: /allowEscapeViewBox/ },
];

test("modal panel never grows beyond the window (its body scrolls instead)", () => {
  const modal = readFileSync(join(SRC, "components/ui/Modal.tsx"), "utf8");
  const panel = modal.match(/<DialogPanel[\s\S]*?className=\{?[`"]([^`"]*)[`"]/)?.[1] ?? "";
  assert.match(panel, /max-h-\[calc\(100dvh/, "DialogPanel must be capped to the window height");
  assert.match(modal, /overflow-y-auto min-h-0/, "Modal body must scroll inside the capped panel");
  assert.doesNotMatch(modal, /items-center[^"`]*overflow-y-auto|overflow-y-auto[^"`]*items-center/,
    "a centred, scrolling overlay hides the top of tall panels");
});

test("floating elements are all built on <Floating>", () => {
  const violations: string[] = [];
  for (const file of files(SRC)) {
    const rel = relative(SRC, file).split(sep).join("/");
    if (ALLOWED.has(rel)) continue;
    const source = readFileSync(file, "utf8");
    for (const rule of RULES) {
      if (rule.pattern.test(source)) violations.push(`${rel}: ${rule.name}`);
    }
  }
  assert.deepEqual(violations, [], "Use components/ui/Floating.tsx (or InfoTooltip) instead:\n" + violations.join("\n"));
});
