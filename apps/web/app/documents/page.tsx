"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Document, Space } from "@/lib/types";
import { SpaceSelector } from "@/components/SpaceSelector";
import { AuthGuard } from "@/lib/auth-guard";
import { AddDocumentModal } from "@/components/documents/AddDocumentModal";

const STATE_STYLES: Record<string, string> = {
  ingested: "bg-yellow-100 text-yellow-800",
  published: "bg-green-100 text-green-800",
  archived: "bg-slate-100 text-slate-600",
};

export default function DocumentsPage() {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingSpaces, setLoadingSpaces] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [spacesError, setSpacesError] = useState<string | null>(null);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    api.get<{ spaces: Space[] }>("/v1/spaces")
      .then((data) => setSpaces(data.spaces))
      .catch((err) => setSpacesError(err.message ?? "Failed to load spaces"))
      .finally(() => setLoadingSpaces(false));
  }, []);

  useEffect(() => {
    if (!selectedSpaceId) return;
    setLoadingDocs(true);
    setDocsError(null);
    api.get<{ documents: Document[] }>(`/v1/documents?space_id=${selectedSpaceId}`)
      .then((data) => setDocuments(data.documents))
      .catch((err) => setDocsError(err.message ?? "Failed to load documents"))
      .finally(() => setLoadingDocs(false));
  }, [selectedSpaceId]);

  const handleDocumentCreated = (newDoc: Document) => {
    if (!selectedSpaceId || newDoc.space_id === selectedSpaceId) {
      setDocuments((prev) => [newDoc, ...prev]);
    }
  };

  return (
    <AuthGuard>
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Documents</h1>
        <button
          onClick={() => setShowModal(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700"
        >
          Add Document
        </button>
      </div>
      <AddDocumentModal
        open={showModal}
        spaces={spaces}
        onClose={() => setShowModal(false)}
        onCreated={handleDocumentCreated}
      />

      <div className="flex items-center gap-3">
        {loadingSpaces ? (
          <p className="text-sm text-slate-500">Loading spaces…</p>
        ) : spacesError ? (
          <p className="text-sm text-red-600">{spacesError}</p>
        ) : (
          <SpaceSelector
            spaces={spaces}
            selectedId={selectedSpaceId}
            onChange={(id) => {
              setSelectedSpaceId(id);
              setDocuments([]);
            }}
          />
        )}
      </div>

      {!selectedSpaceId && !loadingSpaces && (
        <p className="text-sm text-slate-500">Select a space to see its documents.</p>
      )}

      {loadingDocs && <p className="text-sm text-slate-500">Loading documents…</p>}

      {docsError && <p className="text-sm text-red-600">{docsError}</p>}

      {selectedSpaceId && !loadingDocs && !docsError && documents.length === 0 && (
        <p className="text-sm text-slate-500">No documents in this space.</p>
      )}

      {documents.length > 0 && (
        <div className="bg-white rounded border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">Title</th>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">State</th>
                  <th className="text-left px-4 py-2 font-medium text-slate-600 hidden md:table-cell">Confidentiality</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="border-b hover:bg-slate-50">
                    <td className="px-4 py-2">
                      <a href={`/documents/${doc.id}`} className="font-medium text-indigo-600 hover:underline">
                        {doc.title}
                      </a>
                    </td>
                    <td className="px-4 py-2">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATE_STYLES[doc.state] ?? "bg-slate-100 text-slate-600"}`}>
                        {doc.state}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-500 capitalize hidden md:table-cell">{doc.confidentiality}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
    </AuthGuard>
  );
}
