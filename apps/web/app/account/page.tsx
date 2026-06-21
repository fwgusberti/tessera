"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { authChangePassword } from "@/lib/api";

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

export default function AccountPage() {
  const { status, accessToken } = useAuth();
  const router = useRouter();

  const [current, setCurrent] = useState("");
  const [newPass, setNewPass] = useState("");
  const [confirm, setConfirm] = useState("");
  const [newPassError, setNewPassError] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const successTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login?redirect=/account");
    }
  }, [status, router]);

  useEffect(() => {
    return () => {
      if (successTimer.current) clearTimeout(successTimer.current);
    };
  }, []);

  if (status === "loading" || status === "unauthenticated") return null;

  const handleNewPassBlur = () => {
    const err = validatePasswordStrength(newPass);
    setNewPassError(err ?? "");
  };

  const handleConfirmBlur = () => {
    setConfirmError(confirm && newPass !== confirm ? "Passwords do not match." : "");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    setSuccess(false);

    const strengthErr = validatePasswordStrength(newPass);
    if (strengthErr) {
      setNewPassError(strengthErr);
      return;
    }
    if (newPass !== confirm) {
      setConfirmError("Passwords do not match.");
      return;
    }

    const refreshToken = typeof localStorage !== "undefined" ? localStorage.getItem("tessera_refresh_token") : null;
    if (!refreshToken || !accessToken) {
      setFormError("Session unavailable. Please sign in again.");
      return;
    }

    setSubmitting(true);
    try {
      const data = await authChangePassword({
        currentPassword: current,
        newPassword: newPass,
        confirmNewPassword: confirm,
        refreshToken,
        accessToken,
      });
      if (typeof localStorage !== "undefined") {
        localStorage.setItem("tessera_access_token", data.access_token);
        localStorage.setItem("tessera_refresh_token", data.refresh_token);
        localStorage.setItem("tessera_expires_at", String(Date.now() + data.expires_in * 1000));
      }
      setCurrent("");
      setNewPass("");
      setConfirm("");
      setSuccess(true);
      successTimer.current = setTimeout(() => setSuccess(false), 5000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      if (msg.toLowerCase().includes("incorrect") || msg.toLowerCase().includes("current password")) {
        setFormError("Current password is incorrect.");
      } else {
        setFormError(msg || "Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-dvh py-8 sm:py-12 px-4">
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold text-slate-900 mb-8">Account Settings</h1>

        <div className="bg-white rounded border border-slate-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-800 mb-1">Security</h2>
          <p className="text-sm text-slate-500 mb-5">Update your password below.</p>

          {success && (
            <div className="mb-4 rounded border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              Password updated successfully.
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="current-password" className="block text-sm font-medium text-slate-700 mb-1">
                Current password
              </label>
              <input
                id="current-password"
                type="password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                autoComplete="current-password"
                disabled={submitting}
              />
            </div>

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
    </div>
  );
}
