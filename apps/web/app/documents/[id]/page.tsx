"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Ancestor, Document, DocumentVersion, Space } from "@/lib/types";
import { AuthGuard } from "@/lib/auth-guard";
import { useAuth } from "@/lib/auth";
import { DocumentContent } from "@/components/documents/DocumentContent";
import { VersionHistory } from "@/components/documents/VersionHistory";
import { SpaceBreadcrumb } from "@/components/spaces/SpaceBreadcrumb";

const STATE_STYLES: Record<string, string> = {
  ingested: "bg-yellow-100 text-yellow-800",
  published: "bg-green-100 text-green-800",
  archived: "bg-slate-100 text-slate-600",
};

type SpaceRole = "admin" | "editor" | "viewer";

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [document, setDocument] = useState<Document | null>(null);
  const [currentVersion, setCurrentVersion] = useState<DocumentVersion | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [breadcrumbAncestors, setBreadcrumbAncestors] = useState<Ancestor[] | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMessage, setReindexMessage] = useState<string | null>(null);
  const [reindexError, setReindexError] = useState<string | null>(null);
  const [spaceRole, setSpaceRole] = useState<SpaceRole | null>(null);
  const reindexTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { user } = useAuth();

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

  useEffect(() => {
    const spaceId = document?.space_id;
    if (!spaceId) return;
    Promise.all([
      api.get<{ space: Space }>(`/v1/spaces/${spaceId}`),
      api.get<{ ancestors: Ancestor[] }>(`/v1/spaces/${spaceId}/ancestors`),
    ])
      .then(([spaceData, ancestorsData]) => {
        const space = spaceData?.space;
        const ancestors = ancestorsData?.ancestors;
        if (!space || !Array.isArray(ancestors)) return;
        setBreadcrumbAncestors([...ancestors, { id: space.id, name: space.name, slug: space.slug }]);
      })
      .catch(() => {
        // Defensive: keep the plain "← Documents" fallback link
      });
  }, [document?.space_id]);

  useEffect(() => {
    return () => {
      if (reindexTimerRef.current) clearTimeout(reindexTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const spaceId = document?.space_id;
    if (!spaceId) {
      setSpaceRole(null);
      return;
    }
    api
      .get<{ membership: { role: SpaceRole } }>(`/v1/spaces/${spaceId}/members/me`)
      .then((data) => setSpaceRole(data.membership.role))
      .catch(() => setSpaceRole(null));
  }, [document?.space_id]);

  const handleReindex = async () => {
    if (!document) return;
    if (reindexTimerRef.current) clearTimeout(reindexTimerRef.current);
    setReindexing(true);
    setReindexError(null);
    setReindexMessage(null);
    try {
      await api.post(`/v1/documents/${id}/reindex`, {});
      setReindexMessage("Reindex queued");
      reindexTimerRef.current = setTimeout(() => {
        setReindexMessage(null);
        setReindexing(false);
      }, 3000);
    } catch (err: unknown) {
      setReindexError(err instanceof Error ? err.message : "Failed to queue reindex");
      setReindexing(false);
    }
  };

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

  const canReindex =
    document !== null &&
    document.state === "published" &&
    (user?.id === document.owner_user_id || user?.isAdmin === true);

  const canEditDocument =
    document !== null &&
    (spaceRole === "editor" || spaceRole === "admin" || user?.isAdmin === true);

  return (
    <AuthGuard>
      {loading ? (
        <div className="bg-white rounded border border-slate-200 p-8 text-center text-sm text-slate-500">
          Loading document…
        </div>
      ) : error ? (
        <div className="bg-white rounded border border-slate-200 p-8 text-center text-sm text-red-600">
          {error}
        </div>
      ) : !document ? (
        <div className="bg-white rounded border border-slate-200 p-8 text-center text-sm text-slate-500">
          Document not found.
        </div>
      ) : (
        <div className="space-y-6 max-w-4xl">
          <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
            <div>
              {breadcrumbAncestors ? (
                <SpaceBreadcrumb ancestors={breadcrumbAncestors} currentName={document.title} />
              ) : (
                <a href="/documents" className="text-sm text-indigo-600 hover:underline">← Documents</a>
              )}
              <h1 className="text-2xl font-bold text-slate-900 mt-1">{document.title}</h1>
              <div className="flex items-center gap-3 mt-2">
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATE_STYLES[document.state] ?? "bg-slate-100 text-slate-600"}`}>
                  {document.state}
                </span>
                <span className="text-xs text-slate-500 capitalize">{document.confidentiality}</span>
              </div>
              {document.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {document.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-600"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {canEditDocument && (
              <a
                href={`/documents/${id}/edit`}
                className="bg-white text-indigo-600 border border-indigo-200 px-4 py-2 rounded text-sm font-medium hover:bg-indigo-50 transition-colors"
              >
                Edit
              </a>
            )}

            {document.state === "ingested" && (
              <div className="flex flex-col items-end gap-1">
                <button
                  onClick={handlePublish}
                  disabled={publishing}
                  className="bg-green-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {publishing ? "Publishing…" : "Publish"}
                </button>
                {publishError && (
                  <p role="alert" className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
                    {publishError}
                  </p>
                )}
              </div>
            )}

            {canReindex && (
              <div className="flex flex-col items-end gap-1">
                <button
                  onClick={handleReindex}
                  disabled={reindexing}
                  className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {reindexing ? "Reindexing…" : "Reindex"}
                </button>
                {reindexMessage && (
                  <p className="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1">
                    {reindexMessage}
                  </p>
                )}
                {reindexError && (
                  <p role="alert" className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
                    {reindexError}
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="bg-white rounded border p-6">
            <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">Current Content</h2>
            <DocumentContent version={currentVersion} />
          </div>

          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">Version History</h2>
            <VersionHistory versions={versions} />
          </div>
        </div>
      )}
    </AuthGuard>
  );
}
