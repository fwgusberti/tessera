"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { mapSpaceAccesses, directChildren, isDescendant, type ApiSpaceItem } from "@/lib/spaces";
import type { Ancestor, Document, Space, SpaceAccess } from "@/lib/types";
import { AuthGuard } from "@/lib/auth-guard";
import { FolderGrid } from "@/components/spaces/FolderGrid";
import { SpaceBreadcrumb } from "@/components/spaces/SpaceBreadcrumb";
import { SetParentModal } from "@/components/spaces/SetParentModal";
import { RenameSpaceModal } from "@/components/spaces/RenameSpaceModal";
import { DeleteSpaceModal } from "@/components/spaces/DeleteSpaceModal";
import { AddSpaceModal } from "@/components/spaces/AddSpaceModal";
import { AddDocumentModal } from "@/components/documents/AddDocumentModal";

export default function SpaceFolderPage() {
  const params = useParams();
  const folderId = params?.id as string;

  const [accesses, setAccesses] = useState<SpaceAccess[]>([]);
  const [ancestors, setAncestors] = useState<Ancestor[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [managingSpace, setManagingSpace] = useState<Space | null>(null);
  const [renamingSpace, setRenamingSpace] = useState<Space | null>(null);
  const [deletingSpace, setDeletingSpace] = useState<Space | null>(null);
  const [addingSpace, setAddingSpace] = useState(false);
  const [addingDocument, setAddingDocument] = useState(false);

  useEffect(() => {
    if (!folderId) return;
    setLoading(true);
    setError(null);
    Promise.all([
      api.get<{ spaces: ApiSpaceItem[] }>("/v1/spaces"),
      api.get<{ ancestors: Ancestor[] }>(`/v1/spaces/${folderId}/ancestors`),
      api.get<{ documents: Document[] }>(`/v1/documents?space_id=${folderId}`),
    ])
      .then(([spacesData, ancestorsData, documentsData]) => {
        setAccesses(mapSpaceAccesses(spacesData.spaces ?? []));
        setAncestors(ancestorsData.ancestors ?? []);
        setDocuments(documentsData.documents ?? []);
      })
      .catch((err: Error) => setError(err.message ?? "Failed to load folder"))
      .finally(() => setLoading(false));
  }, [folderId]);

  function handleSpaceUpdated(updated: Space) {
    setAccesses((prev) =>
      prev.map((a) => (a.space.id === updated.id ? { ...a, space: updated } : a))
    );
  }

  function handleSpaceDeleted(deletedId: string) {
    setAccesses((prev) =>
      prev.filter((a) => a.space.id !== deletedId && !isDescendant(prev, deletedId, a.space.id))
    );
  }

  function handleDocumentCreated(created: Document) {
    if (created.space_id === folderId) {
      setDocuments((prev) => [...prev, created]);
    }
    setAddingDocument(false);
  }

  function handleSpaceCreated(created: Space) {
    setAccesses((prev) => [
      ...prev,
      { space: created, effective_role: "admin" as const, is_direct: true },
    ]);
  }

  const folder = accesses.find((a) => a.space.id === folderId)?.space ?? null;
  const currentRole = accesses.find((a) => a.space.id === folderId)?.effective_role;
  const canAddDocument = currentRole === "editor" || currentRole === "admin";
  const subfolders = directChildren(accesses, folderId);
  const isEmpty = subfolders.length === 0 && documents.length === 0;

  return (
    <AuthGuard>
      <div className="space-y-6">
        {loading && <p className="text-sm text-slate-500">Loading spaces…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && folder && (
          <>
            <SpaceBreadcrumb
              ancestors={ancestors}
              currentName={folder.name}
              allAccesses={accesses}
              onReparented={handleSpaceUpdated}
            />
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold text-slate-900">{folder.name}</h1>
              <div className="flex items-center gap-3">
                {canAddDocument && (
                  <button
                    onClick={() => setAddingDocument(true)}
                    className="px-4 py-2 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700"
                  >
                    Add Document
                  </button>
                )}
                <button
                  onClick={() => setAddingSpace(true)}
                  className="px-4 py-2 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700"
                >
                  Add Space
                </button>
              </div>
            </div>
            {isEmpty ? (
              <p className="text-sm text-slate-500">This folder has no sub-folders or documents.</p>
            ) : (
              <FolderGrid
                subfolders={subfolders}
                documents={documents}
                allAccesses={accesses}
                onReparented={handleSpaceUpdated}
                onSetParent={(space) => setManagingSpace(space)}
                onRename={(space) => setRenamingSpace(space)}
                onDelete={(space) => setDeletingSpace(space)}
              />
            )}
          </>
        )}
        {managingSpace && (
          <SetParentModal
            space={managingSpace}
            accessibleSpaces={accesses}
            onClose={() => setManagingSpace(null)}
            onUpdated={handleSpaceUpdated}
          />
        )}
        {renamingSpace && (
          <RenameSpaceModal
            space={renamingSpace}
            onClose={() => setRenamingSpace(null)}
            onUpdated={handleSpaceUpdated}
          />
        )}
        {deletingSpace && (
          <DeleteSpaceModal
            space={deletingSpace}
            allAccesses={accesses}
            onClose={() => setDeletingSpace(null)}
            onDeleted={(deletedId) => {
              handleSpaceDeleted(deletedId);
              setDeletingSpace(null);
            }}
          />
        )}
        <AddDocumentModal
          open={addingDocument}
          spaces={accesses.map((a) => a.space)}
          initialSpaceId={folderId}
          onClose={() => setAddingDocument(false)}
          onCreated={handleDocumentCreated}
        />
        {addingSpace && (
          <AddSpaceModal
            parentSpaceId={folderId}
            onClose={() => setAddingSpace(false)}
            onCreated={(created) => {
              handleSpaceCreated(created);
              setAddingSpace(false);
            }}
          />
        )}
      </div>
    </AuthGuard>
  );
}
