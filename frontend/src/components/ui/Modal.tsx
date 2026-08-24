"use client";

import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import { X } from "lucide-react";

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
      <div className="fixed inset-0 flex items-center justify-center p-4 overflow-y-auto">
        <DialogPanel className={`w-full ${maxWidth} bg-white rounded-xl shadow-lg my-8`}>
          <div className="flex items-center justify-between px-5 py-4 border-b">
            <DialogTitle className="text-sm font-semibold text-gray-800">{title}</DialogTitle>
            <button
              type="button"
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Fermer"
            >
              <X size={18} />
            </button>
          </div>
          <div className="p-5">{children}</div>
        </DialogPanel>
      </div>
    </Dialog>
  );
}
