"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { completeOnboarding, getOnboardingStatus } from "@/lib/onboarding";

export default function CompletePage() {
  const router = useRouter();
  const [joinMethod, setJoinMethod] = useState<"created" | "joined" | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);

  useEffect(() => {
    getOnboardingStatus()
      .then((status) => {
        setJoinMethod(status.company_join_method);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleGoToDashboard() {
    setCompleting(true);
    try {
      await completeOnboarding();
    } catch {
      // If already completed, proceed anyway
    }
    router.replace("/");
  }

  if (loading) return null;

  const isJoiner = joinMethod === "joined";

  return (
    <div className="text-center space-y-6">
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
        <svg className="w-8 h-8 text-green-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </div>

      {isJoiner ? (
        <>
          <h2 className="text-2xl font-bold text-slate-900">You&apos;re all set!</h2>
          <p className="text-slate-500">
            You&apos;ve successfully joined your company on Tessera. Welcome aboard!
          </p>
        </>
      ) : (
        <>
          <h2 className="text-2xl font-bold text-slate-900">Your workspace is ready!</h2>
          <p className="text-slate-500">
            You&apos;ve set up your profile and company. Team members you invited will receive email invitations.
          </p>
        </>
      )}

      <button
        onClick={handleGoToDashboard}
        disabled={completing}
        className="w-full bg-indigo-600 text-white rounded px-4 py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
      >
        {completing ? "Setting up…" : "Go to Dashboard"}
      </button>
    </div>
  );
}
