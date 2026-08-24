import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { DataFreshnessBar } from "@/components/layout/DataFreshnessBar";

export const metadata: Metadata = {
  title: "CRISalid Benchmark",
  description: "Outil de benchmarking bibliométrique pour établissements d'enseignement supérieur et de recherche",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <DataFreshnessBar />
            <main className="flex-1 p-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
