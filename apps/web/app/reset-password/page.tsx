"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authResetPassword } from "@/lib/api";

const WEAK_PASSWORDS = new Set([
  "password", "password1", "password123",
  "12345678", "123456789", "1234567890",
  "qwerty12", "qwerty123", "qwertyui",
  "letmein1", "letmein!", "welcome1",
  "monkey12", "dragon12", "master12",
  "sunshine", "princess", "iloveyou",
  "football", "superman", "batman123",
]);

function validatePasswordStrength(password: string): string | null {
  if (password.length < 8) return "Password must be at least 8 characters long.";
  if (WEAK_PASSWORDS.has(password.toLowerCase())) return "Please choose a less common password.";
  if (new Set(password).size === 1) return "Password is too simple. Please use a mix of characters.";
  return null;
}

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [newPass, setNewPass] = useState("");
  const [confirm, setConfirm] = useState("");
  const [newPassError, setNewPassError] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [tokenInvalid, setTokenInvalid] = useState(!token);

  if (tokenInvalid) {
    return (
      <div className="min-h-dvh flex items-center justify-center py-8 sm:py-12">
        <div className="bg-white rounded border border-slate-200 p-8 w-full max-w-sm shadow-sm text-center">
          <h1 className="text-xl font-bold text-slate-900 mb-3">Reset link expired</h1>
          <p className="text-sm text-slate-600 mb-6">
            This reset link has expired or has already been used.
          </p>
          <a
            href="/forgot-password"
            className="inline-block bg-indigo-600 text-white py-2 px-4 rounded text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Request a new link
          </a>
        </div>
      </div>
    );
  }

  const handleNewPassBlur = () => {
    setNewPassError(validatePasswordStrength(newPass) ?? "");
  };

  const handleConfirmBlur = () => {
    setConfirmError(confirm && newPass !== confirm ? "Passwords do not match." : "");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    const strengthErr = validatePasswordStrength(newPass);
    if (strengthErr) {
      setNewPassError(strengthErr);
      return;
    }
    if (newPass !== confirm) {
      setConfirmError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await authResetPassword({ token: token!, newPassword: newPass, confirmNewPassword: confirm });
      router.push("/login?reset=success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.toLowerCase().includes("invalid") || msg.toLowerCase().includes("expired")) {
        setTokenInvalid(true);
      } else {
        setFormError(msg || "Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center justify-center py-8 sm:py-12">
      <div className="bg-white rounded border border-slate-200 p-8 w-full max-w-sm shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">Set a new password</h1>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="new-password" className="block text-sm font-medium text-slate-700 mb-1">
              New password
            </label>
            <input
              id="new-password"
              type="password"
              value={newPass}
              onChange={(e) => { setNewPass(e.target.value); setNewPassError(""); }}
              onBlur={handleNewPassBlur}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              autoComplete="new-password"
              disabled={submitting}
            />
            {newPassError && (
              <p role="alert" className="text-xs text-red-600 mt-1">{newPassError}</p>
            )}
          </div>
          <div>
            <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-700 mb-1">
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type="password"
              value={confirm}
              onChange={(e) => { setConfirm(e.target.value); setConfirmError(""); }}
              onBlur={handleConfirmBlur}
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              autoComplete="new-password"
              disabled={submitting}
            />
            {confirmError && (
              <p role="alert" className="text-xs text-red-600 mt-1">{confirmError}</p>
            )}
          </div>
          {formError && (
            <p role="alert" className="text-sm text-red-600">{formError}</p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-600 text-white py-2 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? "Updating…" : "Update password"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
