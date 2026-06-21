"use client";

type Role = "admin" | "editor" | "viewer";

interface RoleBadgeProps {
  role: Role;
}

const ROLE_STYLES: Record<Role, string> = {
  admin: "bg-indigo-100 text-indigo-700",
  editor: "bg-slate-100 text-slate-700",
  viewer: "bg-slate-50 text-slate-500",
};

export function RoleBadge({ role }: RoleBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ROLE_STYLES[role]}`}
    >
      {role}
    </span>
  );
}
