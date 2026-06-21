"use client";

import type { Space } from "@/lib/types";

interface SpaceSelectorProps {
  spaces: Space[];
  selectedId: string | null;
  onChange: (id: string) => void;
  disabled?: boolean;
}

export function SpaceSelector({ spaces, selectedId, onChange, disabled }: SpaceSelectorProps) {
  return (
    <select
      value={selectedId ?? ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white disabled:opacity-50"
    >
      <option value="">Select a space...</option>
      {spaces.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name}
        </option>
      ))}
    </select>
  );
}
