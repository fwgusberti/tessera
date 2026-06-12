"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Metrics, Space } from "@/lib/types";

interface StatCardProps {
  label: string;
  value: string | number;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="bg-white rounded border p-5">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
    </div>
  );
}

interface NavCardProps {
  href: string;
  title: string;
  description: string;
}

function NavCard({ href, title, description }: NavCardProps) {
  return (
    <a
      href={href}
      className="block bg-white rounded border p-5 hover:border-blue-400 hover:shadow-sm transition-all"
    >
      <p className="font-semibold text-gray-900 mb-1">{title}</p>
      <p className="text-sm text-gray-500">{description}</p>
    </a>
  );
}

export default function Home() {
  const [spaceCount, setSpaceCount] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<Pick<Metrics, "total_queries" | "documents_with_drift"> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<{ spaces: Space[] }>("/v1/spaces"),
      api.get<Metrics>("/v1/metrics"),
    ])
      .then(([spacesData, metricsData]) => {
        setSpaceCount(spacesData.spaces.length);
        setMetrics({
          total_queries: metricsData.total_queries,
          documents_with_drift: metricsData.documents_with_drift,
        });
      })
      .catch(() => {
        setSpaceCount(null);
        setMetrics(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const dash = "–";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Tessera</h1>
        <p className="text-gray-500 mt-1">Living Documentation Platform</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {loading ? (
          <>
            <StatCard label="Spaces" value="…" />
            <StatCard label="Total Queries" value="…" />
            <StatCard label="Documents with Drift" value="…" />
          </>
        ) : (
          <>
            <StatCard label="Spaces" value={spaceCount ?? dash} />
            <StatCard label="Total Queries" value={metrics?.total_queries ?? dash} />
            <StatCard label="Documents with Drift" value={metrics?.documents_with_drift ?? dash} />
          </>
        )}
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Quick Navigation</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <NavCard href="/search" title="Search" description="Semantic search and AI assistant across your documentation" />
          <NavCard href="/proposals" title="Proposals" description="Review and approve pending document update proposals" />
          <NavCard href="/metrics" title="Metrics" description="Platform usage statistics and document health indicators" />
          <NavCard href="/admin" title="Admin" description="Manage spaces, permissions, connectors, and credentials" />
        </div>
      </div>
    </div>
  );
}
