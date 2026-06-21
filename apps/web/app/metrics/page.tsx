"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AuthGuard } from "@/lib/auth-guard";

interface Metrics {
  correct_answer_rate: number | null;
  dont_know_rate: number | null;
  documents_with_drift: number;
  time_to_approval_p50: number | null;
  time_to_approval_p90: number | null;
  total_queries: number;
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded border p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Metrics>("/v1/metrics")
      .then(setMetrics)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const fmt = (v: number | null, suffix = "") =>
    v === null ? "N/A" : `${(v * 100).toFixed(1)}${suffix}`;

  return (
    <AuthGuard>
      {loading ? (
        <p className="text-slate-500">Loading metrics...</p>
      ) : !metrics ? (
        <p className="text-red-500">Failed to load metrics.</p>
      ) : (
        <div className="space-y-6">
          <h1 className="text-2xl font-bold">Product Metrics</h1>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <MetricCard label="Correct Answer Rate" value={fmt(metrics.correct_answer_rate, "%")} />
            <MetricCard label="Don't Know Rate" value={fmt(metrics.dont_know_rate, "%")} />
            <MetricCard label="Documents with Drift" value={String(metrics.documents_with_drift)} />
            <MetricCard label="Total Queries" value={String(metrics.total_queries)} />
            <MetricCard
              label="Approval Time p50"
              value={metrics.time_to_approval_p50 !== null ? `${metrics.time_to_approval_p50}h` : "N/A"}
            />
            <MetricCard
              label="Approval Time p90"
              value={metrics.time_to_approval_p90 !== null ? `${metrics.time_to_approval_p90}h` : "N/A"}
            />
          </div>
        </div>
      )}
    </AuthGuard>
  );
}
