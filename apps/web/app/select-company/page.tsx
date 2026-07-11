"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { getMyCompanies, type CompanyEntry } from "@/lib/companies";

function sanitizeRedirect(redirect: string | null): string {
  return redirect && redirect.startsWith("/") && !redirect.startsWith("//") ? redirect : "/";
}

function selectionErrorMessage(err: unknown): string {
  const code = err instanceof ApiError ? err.code : null;
  if (code === "company_suspended") {
    return "This company's account is suspended and can't be opened right now. You can pick another company or contact your administrator.";
  }
  if (code === "not_a_member") {
    return "You no longer have access to this company. Pick another company to continue.";
  }
  return "Something went wrong. Please try again later.";
}

function SelectCompanyContent() {
  const { status, user, selectTenant, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const dest = sanitizeRedirect(searchParams.get("redirect"));

  const [companies, setCompanies] = useState<CompanyEntry[] | null>(null);
  const [error, setError] = useState("");
  const [pickingId, setPickingId] = useState<string | null>(null);

  const isSelectSession = status === "authenticated" && user?.tokenKind === "select";

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated" || !user) return;
    if (user.tokenKind === "full") {
      router.replace(dest);
    } else if (user.tokenKind === "onboarding") {
      router.replace("/onboarding");
    }
  }, [status, user, dest, router]);

  const loadCompanies = useCallback(() => {
    getMyCompanies()
      .then(setCompanies)
      .catch(() => setError("Something went wrong. Please try again later."));
  }, []);

  useEffect(() => {
    if (!isSelectSession) return;
    loadCompanies();
  }, [isSelectSession, loadCompanies]);

  if (!isSelectSession) return null;

  const handlePick = async (companyId: string) => {
    setPickingId(companyId);
    setError("");
    try {
      await selectTenant(companyId);
      router.push(dest);
    } catch (err: unknown) {
      setError(selectionErrorMessage(err));
      setPickingId(null);
      loadCompanies();
    }
  };

  const handleSignOut = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="min-h-dvh flex items-center justify-center py-8 sm:py-12">
      <div className="bg-white rounded border p-8 w-full max-w-sm shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Choose a company</h1>
        <p className="text-sm text-slate-600 mb-6">
          Your account belongs to more than one company. Pick the one you want to work in.
        </p>
        {error && (
          <p role="alert" className="text-sm text-red-600 mb-4">
            {error}
          </p>
        )}
        {companies === null ? (
          <p className="text-sm text-slate-500">Loading companies…</p>
        ) : (
          <ul className="space-y-2">
            {companies.map((company) => (
              <li key={company.id}>
                <button
                  type="button"
                  onClick={() => handlePick(company.id)}
                  disabled={pickingId !== null}
                  className="w-full flex items-center justify-between border border-slate-300 rounded px-4 py-3 text-left text-sm font-medium text-slate-900 hover:border-indigo-500 hover:bg-indigo-50 disabled:opacity-50 transition-colors"
                >
                  <span>{company.name}</span>
                  <span className="text-xs font-normal text-slate-500 border border-slate-200 rounded px-2 py-0.5">
                    {company.role}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-6 pt-4 border-t border-slate-200 text-center">
          <button
            type="button"
            onClick={handleSignOut}
            className="text-sm text-slate-600 hover:text-slate-900 hover:underline"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SelectCompanyPage() {
  return (
    <Suspense>
      <SelectCompanyContent />
    </Suspense>
  );
}
