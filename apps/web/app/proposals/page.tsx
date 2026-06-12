"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Proposal {
  id: string;
  document_id: string;
  state: string;
  summary: string | null;
  drift_score: number | null;
  proposed_markdown_patch: string;
  created_at: string;
}

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [selected, setSelected] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<{ proposals: Proposal[] }>("/v1/proposals?state=pending")
      .then((data) => setProposals(data.proposals))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await api.post(`/v1/proposals/${id}/approve`, {});
      setProposals((prev) => prev.filter((p) => p.id !== id));
      setSelected(null);
    } catch (err) {
      console.error(err);
    }
  };

  const handleReject = async (id: string) => {
    const reason = window.prompt("Rejection reason (optional):");
    try {
      await api.post(`/v1/proposals/${id}/reject`, { reason });
      setProposals((prev) => prev.filter((p) => p.id !== id));
      setSelected(null);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <p className="text-gray-500">Loading proposals...</p>;

  return (
    <div className="grid grid-cols-3 gap-6">
      <div className="col-span-1 space-y-2">
        <h2 className="text-lg font-semibold mb-4">Pending Proposals ({proposals.length})</h2>
        {proposals.length === 0 && (
          <p className="text-sm text-gray-500">No pending proposals.</p>
        )}
        {proposals.map((p) => (
          <button
            key={p.id}
            onClick={() => setSelected(p)}
            className={`w-full text-left p-3 rounded border text-sm ${
              selected?.id === p.id ? "border-blue-500 bg-blue-50" : "bg-white hover:bg-gray-50"
            }`}
          >
            <p className="font-medium truncate">{p.summary || "Drift detected"}</p>
            <p className="text-xs text-gray-400 mt-1">
              Score: {((p.drift_score || 0) * 100).toFixed(0)}%
            </p>
          </button>
        ))}
      </div>

      <div className="col-span-2">
        {selected ? (
          <div className="bg-white rounded border p-6 space-y-4">
            <h3 className="text-lg font-semibold">{selected.summary || "Proposal Review"}</h3>
            <div className="bg-gray-50 rounded p-4 overflow-auto max-h-96">
              <pre className="text-xs font-mono whitespace-pre-wrap">{selected.proposed_markdown_patch}</pre>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => handleApprove(selected.id)}
                className="bg-green-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-green-700"
              >
                Approve
              </button>
              <button
                onClick={() => handleReject(selected.id)}
                className="bg-red-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-red-700"
              >
                Reject
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded border p-6 text-gray-400 text-sm">
            Select a proposal to review.
          </div>
        )}
      </div>
    </div>
  );
}
