"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Document, DocumentVersion } from "@/lib/types";

const STATE_STYLES: Record<string, string> = {
  ingested: "bg-yellow-100 text-yellow-800",
  published: "bg-green-100 text-green-800",
  archived: "bg-gray-100 text-gray-600",
};

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [document, setDocument] = useState<Document | null>(null);
  const [currentVersion, setCurrentVersion] = useState<DocumentVersion | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.get<{ document: Document; current_version: DocumentVersion | null }>(`/v1/documents/${id}`),
      api.get<{ versions: DocumentVersion[] }>(`/v1/documents/${id}/versions`),
    ])
      .then(([docData, versionsData]) => {
        setDocument(docData.document);
        setCurrentVersion(docData.current_version);
        setVersions(versionsData.versions);
      })
      .catch((err) => setError(err.message ?? "Failed to load document"))
      .finally(() => setLoading(false));
  }, [id]);

  const handlePublish = async () => {
    if (!document) return;
    setPublishing(true);
    setPublishError(null);
    try {
      const data = await api.post<{ document: Document; version: DocumentVersion }>(`/v1/documents/${id}/publish`, {});
      setDocument(data.document);
    } catch (err: unknown) {
      setPublishError(err instanceof Error ? err.message : "Failed to publish document");
    } finally {
      setPublishing(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading document…</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!document) return <p className="text-gray-500">Document not found.</p>;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <a href="/documents" className="text-sm text-blue-600 hover:underline">← Documents</a>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{document.title}</h1>
          <div className="flex items-center gap-3 mt-2">
            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATE_STYLES[document.state] ?? "bg-gray-100 text-gray-600"}`}>
              {document.state}
            </span>
            <span className="text-xs text-gray-500 capitalize">{document.confidentiality}</span>
            {document.tags.length > 0 && (
              <span className="text-xs text-gray-400">{document.tags.join(", ")}</span>
            )}
          </div>
        </div>

        {document.state === "ingested" && (
          <div className="flex flex-col items-end gap-1">
            <button
              onClick={handlePublish}
              disabled={publishing}
              className="bg-green-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {publishing ? "Publishing…" : "Publish"}
            </button>
            {publishError && (
              <p className="text-xs text-red-600">{publishError}</p>
            )}
          </div>
        )}
      </div>

      <div className="bg-white rounded border p-6">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">Current Content</h2>
        {currentVersion ? (
          <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
            {currentVersion.content_markdown}
          </pre>
        ) : (
          <p className="text-sm text-gray-400 italic">No content available for this document.</p>
        )}
      </div>

      <div className="bg-white rounded border overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Version History</h2>
        </div>
        {versions.length === 0 ? (
          <p className="px-4 py-3 text-sm text-gray-400">No versions found.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Version</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Approved At</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Approver</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{v.version_number}</td>
                  <td className="px-4 py-2 text-gray-500">
                    {v.approved_at ? new Date(v.approved_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-2 text-gray-500 font-mono text-xs">
                    {v.approver_user_id ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
