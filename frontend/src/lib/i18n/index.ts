import { fr } from "./fr";

/** All valid dot-paths into the dictionary, e.g. "dashboard.synthesis.title". */
type PathsOf<T, Prefix extends string = ""> = T extends string
  ? Prefix extends `${infer P}.`
    ? P
    : never
  : {
      [K in keyof T & string]: PathsOf<T[K], `${Prefix}${K}.`>;
    }[keyof T & string];

export type TranslationKey = PathsOf<typeof fr>;

const dictionary: Record<string, string> = flatten(fr);

function flatten(obj: unknown, prefix = "", out: Record<string, string> = {}): Record<string, string> {
  if (typeof obj === "string") {
    out[prefix.replace(/\.$/, "")] = obj;
    return out;
  }
  for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
    flatten(value, `${prefix}${key}.`, out);
  }
  return out;
}

/**
 * Look up a wording by key and interpolate `{var}` placeholders. Falls back
 * to the raw key (never throws) so a typo or a not-yet-registered dynamic
 * key degrades visibly instead of crashing the page.
 */
export function t(key: TranslationKey | string, vars?: Record<string, string | number>): string {
  let value = dictionary[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      value = value.replaceAll(`{${k}}`, String(v));
    }
  }
  return value;
}
