"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { type CompanyEntry, type CreateCompanyData, createCompany, getMyCompanies } from "./companies";
import { useAuth } from "./auth";

const LS_ACTIVE_COMPANY_ID = "tessera_active_company_id";

export interface CompanyContextValue {
  companies: CompanyEntry[];
  activeCompany: CompanyEntry | null;
  isLoading: boolean;
  setActiveCompany(id: string): void;
  createAndSetActive(data: CreateCompanyData): Promise<void>;
  reloadCompanies(): Promise<void>;
}

const CompanyContext = createContext<CompanyContextValue | null>(null);

export function useCompany(): CompanyContextValue {
  const ctx = useContext(CompanyContext);
  if (!ctx) throw new Error("useCompany must be used inside CompanyProvider");
  return ctx;
}

export function CompanyProvider({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const [companies, setCompanies] = useState<CompanyEntry[]>([]);
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const reloadCompanies = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await getMyCompanies();
      setCompanies(list);

      const storedId = (() => {
        try { return localStorage.getItem(LS_ACTIVE_COMPANY_ID); } catch { return null; }
      })();

      if (storedId && list.some((c) => c.id === storedId)) {
        setActiveCompanyId(storedId);
      } else if (list.length > 0) {
        setActiveCompanyId(list[0].id);
        try { localStorage.setItem(LS_ACTIVE_COMPANY_ID, list[0].id); } catch { /* ignore */ }
      } else {
        setActiveCompanyId(null);
      }
    } catch {
      // network error — leave prior state
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status === "authenticated") {
      reloadCompanies();
    } else if (status === "unauthenticated") {
      setCompanies([]);
      setActiveCompanyId(null);
    }
  }, [status, reloadCompanies]);

  const setActiveCompany = useCallback((id: string) => {
    setActiveCompanyId(id);
    try { localStorage.setItem(LS_ACTIVE_COMPANY_ID, id); } catch { /* ignore */ }
  }, []);

  const createAndSetActive = useCallback(async (data: CreateCompanyData) => {
    const created = await createCompany(data);
    await reloadCompanies();
    setActiveCompany(created.id);
  }, [reloadCompanies, setActiveCompany]);

  const activeCompany = companies.find((c) => c.id === activeCompanyId) ?? null;

  return (
    <CompanyContext.Provider value={{ companies, activeCompany, isLoading, setActiveCompany, createAndSetActive, reloadCompanies }}>
      {children}
    </CompanyContext.Provider>
  );
}
