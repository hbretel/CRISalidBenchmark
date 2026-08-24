"use client";

import { Switch as HeadlessSwitch } from "@headlessui/react";

interface Props {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
}

/**
 * Toggle switch (MUI react-switch look: pill track + sliding circular thumb),
 * built on @headlessui/react's unstyled Switch primitive rather than a plain
 * checkbox or a fully hand-rolled widget — keyboard/aria behaviour comes for
 * free, only the visual styling below is ours.
 */
export function Switch({ checked, onChange, label, disabled = false }: Props) {
  return (
    <HeadlessSwitch.Group as="div" className="flex items-center gap-2">
      <HeadlessSwitch
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className={`${checked ? "bg-brand-600" : "bg-gray-300"} ${
          disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
        } relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1`}
      >
        <span
          className={`${checked ? "translate-x-4" : "translate-x-0.5"} inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200`}
        />
      </HeadlessSwitch>
      {label && (
        <HeadlessSwitch.Label className="text-sm text-gray-700 cursor-pointer select-none">
          {label}
        </HeadlessSwitch.Label>
      )}
    </HeadlessSwitch.Group>
  );
}
