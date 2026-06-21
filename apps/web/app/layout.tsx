import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { OnboardingGuard } from "@/lib/auth-guard";
import { NavBar } from "@/components/NavBar";

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
        <AuthProvider>
          <OnboardingGuard>
            <div className="min-h-screen bg-slate-50">
              <NavBar />
              <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
            </div>
          </OnboardingGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
