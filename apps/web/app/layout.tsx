import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Tessera",
  description: "Living Documentation Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className={`${inter.className} antialiased`}>
        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
            <a href="/" className="text-xl font-semibold text-gray-900">
              Tessera
            </a>
            <div className="flex items-center gap-4">
              <a href="/search" className="text-sm text-gray-600 hover:text-gray-900">
                Search
              </a>
              <a href="/proposals" className="text-sm text-gray-600 hover:text-gray-900">
                Proposals
              </a>
              <a href="/metrics" className="text-sm text-gray-600 hover:text-gray-900">
                Metrics
              </a>
              <a href="/admin" className="text-sm text-gray-600 hover:text-gray-900">
                Admin
              </a>
            </div>
          </nav>
          <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
