"use client";

type CompanyRole = "admin" | "member";

interface CompanyRoleBadgeProps {
  role: CompanyRole;
}

const ROLE_STYLES: Record<CompanyRole, string> = {
  admin: "bg-indigo-100 text-indigo-700",
  member: "bg-slate-100 text-slate-700",
};

const ROLE_LABELS: Record<CompanyRole, string> = {
  admin: "administrator",
  member: "member",
};

export function CompanyRoleBadge({ role }: CompanyRoleBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ROLE_STYLES[role]}`}
    >
      {ROLE_LABELS[role]}
    </span>
  );
}
