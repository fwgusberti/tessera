"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { cancelJoinRequest, getJoinStatus } from "@/lib/companies";

const POLL_INTERVAL_MS = 5000;

export default function PendingPage() {
  const router = useRouter();
  const params = useSearchParams();
  const companyId = params.get("company") ?? "";

  const [status, setStatus] = useState<"pending" | "approved" | "denied" | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!companyId) return;

    async function poll() {
      try {
        const data = await getJoinStatus(companyId);
        setCompanyName(data.company_name);
        setStatus(data.status);
        if (data.status === "approved") {
          clearInterval(intervalRef.current!);
          router.push("/onboarding/complete");
        } else if (data.status === "denied") {
          clearInterval(intervalRef.current!);
        }
      } catch {
        // transient error — keep polling
      }
    }

    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(intervalRef.current!);
  }, [companyId, router]);

  async function handleCancel() {
    setCancelling(true);
    setError(null);
    try {
      await cancelJoinRequest(companyId);
      router.push("/onboarding/company");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel.");
      setCancelling(false);
    }
  }

  if (!companyId) {
    router.replace("/onboarding/company");
    return null;
  }

  return (
    <div className="text-center space-y-6">
      {status === "denied" ? (
        <>
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-red-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Request Not Approved</h2>
          <p className="text-gray-500">
            Your request to join{companyName ? ` ${companyName}` : ""} was not approved.
          </p>
          <button
            onClick={() => router.push("/onboarding/company")}
            className="w-full bg-blue-600 text-white rounded px-4 py-2 text-sm font-medium hover:bg-blue-700"
          >
            Try Another Company
          </button>
        </>
      ) : (
        <>
          <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto">
            <div className="w-6 h-6 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Pending Approval</h2>
          <p className="text-gray-500">
            Your request to join{companyName ? ` ${companyName}` : ""} is waiting for an admin to review it.
            We&apos;ll notify you by email once a decision is made.
          </p>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {error}
            </p>
          )}

          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="w-full border border-gray-300 text-gray-700 rounded px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            {cancelling ? "Cancelling…" : "Cancel Request"}
          </button>
        </>
      )}
    </div>
  );
}
