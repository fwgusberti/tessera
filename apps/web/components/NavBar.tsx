"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function NavBar() {
  const { status, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <a href="/" className="text-xl font-semibold text-gray-900">
        Tessera
      </a>
      <div className="flex items-center gap-4">
        <a href="/search" className="text-sm text-gray-600 hover:text-gray-900">
          Search
        </a>
        <a href="/documents" className="text-sm text-gray-600 hover:text-gray-900">
          Documents
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
        {status === "authenticated" && (
          <button
            onClick={handleLogout}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Sign out
          </button>
        )}
      </div>
    </nav>
  );
}
