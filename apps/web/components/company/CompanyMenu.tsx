"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useCompany } from "@/lib/company";
import { CreateCompanyModal } from "./CreateCompanyModal";

export function CompanyMenu() {
  const { companies, activeCompany, setActiveCompany } = useCompany();
  const [open, setOpen] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handleKey);
    document.addEventListener("mousedown", handleClick);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("mousedown", handleClick);
    };
  }, [open]);

  if (companies.length === 0) {
    return (
      <span className="text-sm text-slate-500">
        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="text-indigo-600 hover:underline"
        >
          Create or join a company
        </button>
        <CreateCompanyModal open={showModal} onClose={() => setShowModal(false)} />
      </span>
    );
  }

  if (companies.length === 1) {
    return (
      <span className="text-sm font-medium text-slate-700">
        {activeCompany?.name ?? companies[0].name}
      </span>
    );
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-sm font-medium text-slate-700 hover:text-indigo-600 rounded px-2 py-1"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {activeCompany?.name ?? "Select company"}
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-0 top-full mt-1 w-56 rounded-md border border-slate-200 bg-white shadow-lg z-50 py-1"
        >
          {companies.map((c) => (
            <button
              key={c.id}
              role="option"
              aria-selected={c.id === activeCompany?.id}
              type="button"
              onClick={() => {
                setActiveCompany(c.id);
                setOpen(false);
              }}
              className={`w-full text-left px-4 py-2 text-sm hover:bg-slate-50 ${
                c.id === activeCompany?.id ? "font-semibold text-indigo-600" : "text-slate-700"
              }`}
            >
              {c.name}
            </button>
          ))}

          <div className="border-t border-slate-100 mt-1 pt-1">
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                setShowModal(true);
              }}
              className="w-full text-left px-4 py-2 text-sm text-slate-500 hover:bg-slate-50"
            >
              + Create new company
            </button>
            {activeCompany?.role === "admin" && (
              <Link
                href="/settings/company"
                onClick={() => setOpen(false)}
                className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
              >
                Company settings
              </Link>
            )}
          </div>
        </div>
      )}

      <CreateCompanyModal open={showModal} onClose={() => setShowModal(false)} />
    </div>
  );
}
