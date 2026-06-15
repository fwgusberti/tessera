"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";

function LoginForm() {
  const { status, login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/");
    }
  }, [status, router]);

  if (status === "loading" || status === "authenticated") return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError("");
    setPasswordError("");
    setFormError("");

    let hasError = false;
    if (!email.trim()) {
      setEmailError("Email is required");
      hasError = true;
    }
    if (!password) {
      setPasswordError("Password is required");
      hasError = true;
    }
    if (hasError) return;

    setSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      const dest =
        redirect && redirect.startsWith("/") && !redirect.startsWith("//")
          ? redirect
          : "/";
      router.push(dest);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      if (message === "Invalid credentials") {
        setFormError("Invalid credentials. Please check your email and password.");
      } else {
        setFormError("Something went wrong. Please try again later.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center py-12">
      <div className="bg-white rounded border p-8 w-full max-w-sm shadow-sm">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Sign in to Tessera</h1>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoComplete="email"
              disabled={submitting}
            />
            {emailError && (
              <p role="alert" className="text-xs text-red-600 mt-1">
                {emailError}
              </p>
            )}
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoComplete="current-password"
              disabled={submitting}
            />
            {passwordError && (
              <p role="alert" className="text-xs text-red-600 mt-1">
                {passwordError}
              </p>
            )}
          </div>
          {formError && (
            <p role="alert" className="text-sm text-red-600">
              {formError}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-blue-600 text-white py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
