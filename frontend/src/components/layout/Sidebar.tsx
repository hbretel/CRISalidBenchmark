"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Settings, Sliders } from "lucide-react";

const NAV_ITEMS = [
  { href: "/",                     icon: Home,    label: "Tableau de bord" },
  { href: "/parametres-benchmark", icon: Sliders, label: "Paramètres du benchmark" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 min-h-screen bg-gray-900 flex flex-col">
      {/* Logo / app name */}
      <div className="px-4 py-5 border-b border-gray-700">
        <span className="text-white font-semibold text-sm leading-tight">
          CRISalid<br />
          <span className="text-brand-400 font-normal">Benchmark</span>
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 flex flex-col gap-0.5 px-2">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
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
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Setup link */}
      <div className="px-2 py-3 border-t border-gray-700">
        <Link
          href="/configuration"
          className="flex items-center gap-3 px-3 py-2 rounded text-sm text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors"
        >
          <Settings size={16} />
          Configuration
        </Link>
      </div>
    </aside>
  );
}
