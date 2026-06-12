"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Space {
  id: string;
  slug: string;
  name: string;
  sector: string;
}

interface Metrics {
  documents_with_drift: number;
  total_queries: number;
}

export default function AdminPage() {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<{ spaces: Space[] }>("/v1/spaces"),
      api.get<Metrics>("/v1/metrics"),
    ])
      .then(([spacesData, metricsData]) => {
        setSpaces(spacesData.spaces);
        setMetrics(metricsData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading admin panel...</p>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Admin Panel</h1>

      {metrics && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded border p-4">
            <p className="text-sm text-gray-500">Documents with Drift</p>
            <p className="text-3xl font-bold text-orange-600">{metrics.documents_with_drift}</p>
          </div>
          <div className="bg-white rounded border p-4">
            <p className="text-sm text-gray-500">Total Queries</p>
            <p className="text-3xl font-bold text-blue-600">{metrics.total_queries}</p>
          </div>
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold mb-4">Spaces ({spaces.length})</h2>
        <div className="bg-white rounded border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Slug</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Sector</th>
              </tr>
            </thead>
            <tbody>
              {spaces.map((space) => (
                <tr key={space.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{space.name}</td>
                  <td className="px-4 py-2 text-gray-500">{space.slug}</td>
                  <td className="px-4 py-2 text-gray-500">{space.sector}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
