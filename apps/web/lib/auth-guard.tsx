"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./auth";
import { api } from "./api";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [status, router, pathname]);

  if (status === "loading" || status === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}

const TENANT_EXEMPT = ["/login", "/register", "/select-company", "/forgot-password", "/reset-password"];

export function TenantGuard({ children }: { children: React.ReactNode }) {
  const { status, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const isExempt = TENANT_EXEMPT.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
  const mustSelect = status === "authenticated" && user?.tokenKind === "select" && !isExempt;

  useEffect(() => {
    if (mustSelect) {
      router.replace(`/select-company?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [mustSelect, router, pathname]);

  if (mustSelect) return null;

  return <>{children}</>;
}

const ONBOARDING_EXEMPT = ["/login", "/register", "/onboarding", "/select-company"];

export function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);
  const fetchedRef = useRef(false);

  const isExempt = ONBOARDING_EXEMPT.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );

  useEffect(() => {
    if (status !== "authenticated" || isExempt || fetchedRef.current) return;
    fetchedRef.current = true;

    api
      .get<{ completed: boolean }>("/v1/onboarding/status")
      .then((data) => {
        if (!data.completed) {
          router.replace("/onboarding");
        } else {
          setChecked(true);
        }
      })
      .catch(() => {
        // If onboarding API isn't available yet, don't block the user
        setChecked(true);
      });
  }, [status, isExempt, router]);

  if (status === "loading") return null;
  if (!isExempt && status === "authenticated" && !checked) return null;

  return <>{children}</>;
}
