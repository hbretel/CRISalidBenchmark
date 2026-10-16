"use client";

import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { X } from "lucide-react";
import { t } from "@/lib/i18n";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  maxWidth?: string;
}

/**
 * Shared modal shell for the "create/edit" flows on Paramètres du benchmark
 * (weight profiles, comparison groups) — same look for both so the two
 * builders read as one consistent pattern, per the spec's "reprend les mêmes
 * codes" requirement.
 */
export function Modal({ open, onClose, title, children, maxWidth = "max-w-lg" }: Props) {
  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      {/* The panel is capped to the window height and its body scrolls inside:
          a centred panel taller than the window would otherwise overflow at
          the top, out of reach (e.g. weight profile with an axis expanded). */}
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel
          data-modal-panel=""
          className={`w-full ${maxWidth} max-h-[calc(100dvh-2rem)] flex flex-col bg-white rounded-xl shadow-lg`}
        >
          <div className="shrink-0 flex items-center justify-between px-5 py-4 border-b">
            <DialogTitle className="text-sm font-semibold text-gray-800">{title}</DialogTitle>
            <button
              type="button"
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              aria-label={t("common.close")}
            >
              <X size={18} />
            </button>
          </div>
          <div className="p-5 overflow-y-auto min-h-0">{children}</div>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
