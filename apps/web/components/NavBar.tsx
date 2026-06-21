"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function NavBar() {
  const { status, logout } = useAuth();
  const router = useRouter();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsMenuOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <nav className="bg-white border-b border-slate-200 px-4 py-3">
      <div className="flex items-center justify-between">
        <a href="/" className="text-xl font-semibold text-slate-900">
          Tessera
        </a>
        {/* Desktop nav links */}
        <div className="hidden md:flex items-center gap-4">
          <a href="/search" className="text-sm text-slate-600 hover:text-slate-900">
            Search
          </a>
          <a href="/documents" className="text-sm text-slate-600 hover:text-slate-900">
            Documents
          </a>
          <a href="/proposals" className="text-sm text-slate-600 hover:text-slate-900">
            Proposals
          </a>
          <a href="/metrics" className="text-sm text-slate-600 hover:text-slate-900">
            Metrics
          </a>
          <a href="/admin" className="text-sm text-slate-600 hover:text-slate-900">
            Admin
          </a>
          {status === "authenticated" && (
            <button
              onClick={handleLogout}
              className="text-sm text-slate-600 hover:text-slate-900"
            >
              Sign out
            </button>
          )}
        </div>
        {/* Hamburger button (mobile only) */}
        <button
          className="md:hidden min-h-[44px] min-w-[44px] flex items-center justify-center text-slate-600 hover:text-slate-900"
          aria-label="Open menu"
          aria-expanded={isMenuOpen}
          onClick={() => setIsMenuOpen((prev) => !prev)}
        >
          {isMenuOpen ? (
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>
      {/* Mobile menu */}
      {isMenuOpen && (
        <div className="md:hidden">
          {/* Backdrop — closes menu when clicking outside the nav panel */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsMenuOpen(false)}
          />
          <div className="relative z-20 border-t border-slate-100 mt-2 pb-2 bg-white">
            <div className="flex flex-col">
              <a
                href="/search"
                onClick={() => setIsMenuOpen(false)}
                className="px-2 py-3 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              >
                Search
              </a>
              <a
                href="/documents"
                onClick={() => setIsMenuOpen(false)}
                className="px-2 py-3 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              >
                Documents
              </a>
              <a
                href="/proposals"
                onClick={() => setIsMenuOpen(false)}
                className="px-2 py-3 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              >
                Proposals
              </a>
              <a
                href="/metrics"
                onClick={() => setIsMenuOpen(false)}
                className="px-2 py-3 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              >
                Metrics
              </a>
              <a
                href="/admin"
                onClick={() => setIsMenuOpen(false)}
                className="px-2 py-3 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              >
                Admin
              </a>
              {status === "authenticated" && (
                <button
                  onClick={async () => {
                    setIsMenuOpen(false);
                    await handleLogout();
                  }}
                  className="px-2 py-3 text-sm text-left text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                >
                  Sign out
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
