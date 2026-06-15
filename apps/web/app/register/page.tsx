"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { authRegister } from "@/lib/api";
import type { PasswordStrength } from "@/lib/types";

function passwordStrength(value: string): PasswordStrength {
  if (value.length < 8) return "weak";
  const classes = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^a-zA-Z0-9]/].filter((re) => re.test(value)).length;
  if (value.length >= 12 || classes >= 2) return "strong";
  return "medium";
}

const strengthLabel: Record<PasswordStrength, string> = {
  weak: "Weak",
  medium: "Medium",
  strong: "Strong",
};

const strengthColor: Record<PasswordStrength, string> = {
  weak: "text-red-500",
  medium: "text-yellow-600",
  strong: "text-green-600",
};

function RegisterForm() {
  const { status, login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect");

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayNameError, setDisplayNameError] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [formError, setFormError] = useState("");
  const [formErrorIsEmail, setFormErrorIsEmail] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/");
    }
  }, [status, router]);

  if (status === "loading" || status === "authenticated") return null;

  const strength = password ? passwordStrength(password) : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setDisplayNameError("");
    setEmailError("");
    setPasswordError("");
    setFormError("");
    setFormErrorIsEmail(false);

    let hasError = false;
    const trimmedName = displayName.trim();
    if (!trimmedName) {
      setDisplayNameError("Display name is required");
      hasError = true;
    } else if (trimmedName.length > 100) {
      setDisplayNameError("Display name must be 100 characters or fewer");
      hasError = true;
    }
    if (!email.trim()) {
      setEmailError("Email is required");
      hasError = true;
    } else if (!email.includes("@") || !email.split("@")[1]?.includes(".")) {
      setEmailError("Enter a valid email address");
      hasError = true;
    }
    if (!password) {
      setPasswordError("Password is required");
      hasError = true;
    } else if (password.length < 8) {
      setPasswordError("Password must be at least 8 characters");
      hasError = true;
    }
    if (hasError) return;

    setSubmitting(true);
    try {
      await authRegister(trimmedName, email.trim(), password);
      await login({ email: email.trim(), password });
      const dest =
        redirect && redirect.startsWith("/") && !redirect.startsWith("//")
          ? redirect
          : "/";
      router.push(dest);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Registration failed";
      if (message === "Email already registered") {
        setFormError("This email is already registered.");
        setFormErrorIsEmail(true);
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
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Create your account</h1>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="displayName" className="block text-sm font-medium text-gray-700 mb-1">
              Display name
            </label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoComplete="name"
              disabled={submitting}
            />
            {displayNameError && (
              <p role="alert" className="text-xs text-red-600 mt-1">
                {displayNameError}
              </p>
            )}
          </div>
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
              autoComplete="new-password"
              disabled={submitting}
            />
            {strength && (
              <p className={`text-xs mt-1 ${strengthColor[strength]}`}>
                Password strength: {strengthLabel[strength]}
              </p>
            )}
            {passwordError && (
              <p role="alert" className="text-xs text-red-600 mt-1">
                {passwordError}
              </p>
            )}
          </div>
          {formError && (
            <p role="alert" className="text-sm text-red-600">
              {formError}{" "}
              {formErrorIsEmail && (
                <a href="/login" className="underline">
                  Sign in instead?
                </a>
              )}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-blue-600 text-white py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
          <p className="text-sm text-center text-gray-600">
            Already have an account?{" "}
            <a href="/login" className="text-blue-600 hover:underline">
              Sign in
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
