import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { DataFreshnessBar } from "@/components/layout/DataFreshnessBar";
import { AuthGate } from "@/components/layout/AuthGate";

export const metadata: Metadata = {
  title: "CRISalid Benchmark",
  description: "Outil de benchmarking bibliométrique pour établissements d'enseignement supérieur et de recherche",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <div className="flex h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
            <DataFreshnessBar />
            <main className="flex-1 p-6">
              <AuthGate>{children}</AuthGate>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
