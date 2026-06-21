"use client";

import { useState } from "react";
import { authForgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (submitted) {
    return (
      <div className="min-h-dvh flex items-center justify-center py-8 sm:py-12">
        <div className="bg-white rounded border border-slate-200 p-8 w-full max-w-sm shadow-sm text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-4">Check your email</h1>
          <p className="text-sm text-slate-600 mb-6">
            If that email is registered, you will receive a reset link shortly.
          </p>
          <a href="/login" className="text-sm text-indigo-600 hover:underline">
            Back to sign in
          </a>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError("");

    if (!email.trim()) {
      setEmailError("Email is required");
      return;
    }

    setSubmitting(true);
    try {
      await authForgotPassword(email.trim());
    } catch {
      // Always show the success state regardless of outcome (non-enumeration)
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  };

  return (
    <div className="min-h-dvh flex items-center justify-center py-8 sm:py-12">
      <div className="bg-white rounded border border-slate-200 p-8 w-full max-w-sm shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Reset your password</h1>
        <p className="text-sm text-slate-500 mb-6">
          Enter your email address and we&apos;ll send you a reset link.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              autoComplete="email"
              disabled={submitting}
            />
            {emailError && (
              <p role="alert" className="text-xs text-red-600 mt-1">
                {emailError}
              </p>
            )}
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-600 text-white py-2 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? "Sending…" : "Send reset link"}
          </button>
          <p className="text-sm text-center text-slate-600">
            <a href="/login" className="text-indigo-600 hover:underline">
              Back to sign in
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}
