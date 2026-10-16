"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ClipboardCheck, Home, LogOut, Settings, Sliders } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { t } from "@/lib/i18n";

const NAV_ITEMS = [
  { href: "/",                     icon: Home,    labelKey: "nav.dashboard" },
  { href: "/parametres-benchmark", icon: Sliders, labelKey: "nav.settings" },
  { href: "/parametres-qualite",   icon: ClipboardCheck, labelKey: "nav.qualitySettings" },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, mutate } = useAuth();

  async function handleLogout() {
    await api.post("/auth/logout", {});
    mutate(undefined, { revalidate: false });
    router.push("/login");
  }

  return (
    <aside className="w-56 h-screen sticky top-0 bg-gray-900 flex flex-col shrink-0">
      {/* Logo / app name */}
      <div className="px-4 py-5 border-b border-gray-700 shrink-0">
        <span className="text-white font-semibold text-sm leading-tight">
          CRISalid<br />
          <span className="text-brand-400 font-normal">Benchmark</span>
        </span>
      </div>

      {/* Navigation — scrolls internally so the footer below stays pinned */}
      <nav className="flex-1 py-4 flex flex-col gap-0.5 px-2 overflow-y-auto">
        {NAV_ITEMS.map(({ href, icon: Icon, labelKey }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
                active
                  ? "bg-brand-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              <Icon size={16} />
              {t(labelKey)}
            </Link>
          );
        })}
      </nav>

      {/* Configuration / logout — always visible at the bottom, no scroll required */}
      <div className="px-2 py-3 border-t border-gray-700 shrink-0 flex flex-col gap-0.5">
        <Link
          href="/configuration"
          className="flex items-center gap-3 px-3 py-2 rounded text-sm text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors"
        >
          <Settings size={16} />
          {t("nav.configuration")}
        </Link>
        {isAuthenticated && (
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 rounded text-sm text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors text-left"
          >
            <LogOut size={16} />
            {t("nav.logout")}
          </button>
        )}
      </div>
    </aside>
  );
}
