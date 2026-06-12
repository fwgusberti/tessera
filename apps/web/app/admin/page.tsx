"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Space, Metrics } from "@/lib/types";
import { SpaceSelector } from "@/components/SpaceSelector";

export default function AdminPage() {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);

  // Create Space form state
  const [spaceSlug, setSpaceSlug] = useState("");
  const [spaceName, setSpaceName] = useState("");
  const [spaceSector, setSpaceSector] = useState("");
  const [spaceLang, setSpaceLang] = useState("pt-BR");
  const [spaceFormError, setSpaceFormError] = useState<string | null>(null);
  const [spaceFormSuccess, setSpaceFormSuccess] = useState<string | null>(null);
  const [spaceSubmitting, setSpaceSubmitting] = useState(false);

  // Permissions form state
  const [permSpaceId, setPermSpaceId] = useState<string | null>(null);
  const [permGroup, setPermGroup] = useState("");
  const [permRole, setPermRole] = useState("viewer");
  const [permConfidentiality, setPermConfidentiality] = useState("internal");
  const [permError, setPermError] = useState<string | null>(null);
  const [permSuccess, setPermSuccess] = useState<string | null>(null);
  const [permSubmitting, setPermSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get<{ spaces: Space[] }>("/v1/admin/spaces"),
      api.get<Metrics>("/v1/metrics"),
    ])
      .then(([spacesData, metricsData]) => {
        setSpaces(spacesData.spaces);
        setMetrics(metricsData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleCreateSpace = async (e: React.FormEvent) => {
    e.preventDefault();
    setSpaceFormError(null);
    setSpaceFormSuccess(null);

    if (!spaceSlug.trim()) {
      setSpaceFormError("Slug is required.");
      return;
    }
    if (!spaceName.trim()) {
      setSpaceFormError("Name is required.");
      return;
    }
    if (!spaceSector.trim()) {
      setSpaceFormError("Sector is required.");
      return;
    }

    setSpaceSubmitting(true);
    try {
      const data = await api.post<{ space: Space }>("/v1/spaces", {
        slug: spaceSlug.trim(),
        name: spaceName.trim(),
        sector: spaceSector.trim(),
        default_language: spaceLang.trim() || "pt-BR",
      });
      setSpaces((prev) => [...prev, data.space]);
      setSpaceSlug("");
      setSpaceName("");
      setSpaceSector("");
      setSpaceLang("pt-BR");
      setSpaceFormSuccess("Space created successfully.");
    } catch (err: unknown) {
      setSpaceFormError(err instanceof Error ? err.message : "Failed to create space.");
    } finally {
      setSpaceSubmitting(false);
    }
  };

  const handleAddPermission = async (e: React.FormEvent) => {
    e.preventDefault();
    setPermError(null);
    setPermSuccess(null);

    if (!permSpaceId) {
      setPermError("Select a space.");
      return;
    }
    if (!permGroup.trim()) {
      setPermError("IDP group is required.");
      return;
    }

    setPermSubmitting(true);
    try {
      await api.post(`/v1/spaces/${permSpaceId}/permissions`, {
        idp_group: permGroup.trim(),
        role: permRole,
        max_confidentiality: permConfidentiality,
      });
      setPermGroup("");
      setPermRole("viewer");
      setPermConfidentiality("internal");
      setPermSuccess("Permission added.");
    } catch (err: unknown) {
      setPermError(err instanceof Error ? err.message : "Failed to add permission.");
    } finally {
      setPermSubmitting(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading admin panel…</p>;

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-bold">Admin Panel</h1>

      {/* Metrics summary */}
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

      {/* Spaces table */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Spaces ({spaces.length})</h2>
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
              {spaces.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-3 text-sm text-gray-400">No spaces yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Create Space form */}
        <div className="bg-white rounded border p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Create Space</h3>
          <form onSubmit={handleCreateSpace} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Slug (e.g. engineering)"
              value={spaceSlug}
              onChange={(e) => setSpaceSlug(e.target.value)}
              className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="Name (e.g. Engineering)"
              value={spaceName}
              onChange={(e) => setSpaceName(e.target.value)}
              className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="Sector (e.g. Technology)"
              value={spaceSector}
              onChange={(e) => setSpaceSector(e.target.value)}
              className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="Language (default: pt-BR)"
              value={spaceLang}
              onChange={(e) => setSpaceLang(e.target.value)}
              className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="sm:col-span-2 flex items-center gap-3">
              <button
                type="submit"
                disabled={spaceSubmitting}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {spaceSubmitting ? "Creating…" : "Create Space"}
              </button>
              {spaceFormError && <p className="text-sm text-red-600">{spaceFormError}</p>}
              {spaceFormSuccess && <p className="text-sm text-green-600">{spaceFormSuccess}</p>}
            </div>
          </form>
        </div>
      </section>

      {/* Space Permissions */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Space Permissions</h2>
        <div className="bg-white rounded border p-5">
          <form onSubmit={handleAddPermission} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <SpaceSelector
              spaces={spaces}
              selectedId={permSpaceId}
              onChange={setPermSpaceId}
              disabled={permSubmitting}
            />
            <input
              type="text"
              placeholder="IDP Group (e.g. engineering-team)"
              value={permGroup}
              onChange={(e) => setPermGroup(e.target.value)}
              className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={permRole}
              onChange={(e) => setPermRole(e.target.value)}
              className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
              <option value="admin">Admin</option>
            </select>
            <select
              value={permConfidentiality}
              onChange={(e) => setPermConfidentiality(e.target.value)}
              className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="confidential">Confidential</option>
            </select>
            <div className="sm:col-span-2 flex items-center gap-3">
              <button
                type="submit"
                disabled={permSubmitting}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {permSubmitting ? "Adding…" : "Add Permission"}
              </button>
              {permError && <p className="text-sm text-red-600">{permError}</p>}
              {permSuccess && <p className="text-sm text-green-600">{permSuccess}</p>}
            </div>
          </form>
        </div>
      </section>

      <ConnectorsSection spaces={spaces} />
      <AgentCredentialsSection spaces={spaces} />
    </div>
  );
}

// --- Connectors Section ---

interface SessionConnector {
  id: string;
  type: string;
  schedule: string | null;
  jobId?: string;
}

function ConnectorsSection({ spaces }: { spaces: Space[] }) {
  const [connectorSpaceId, setConnectorSpaceId] = useState<string | null>(null);
  const [connectorType, setConnectorType] = useState("");
  const [connectorConfig, setConnectorConfig] = useState("");
  const [connectorSchedule, setConnectorSchedule] = useState("");
  const [connectorError, setConnectorError] = useState<string | null>(null);
  const [connectorSubmitting, setConnectorSubmitting] = useState(false);
  const [sessionConnectors, setSessionConnectors] = useState<SessionConnector[]>([]);
  const [syncErrors, setSyncErrors] = useState<Record<string, string>>({});

  const handleCreateConnector = async (e: React.FormEvent) => {
    e.preventDefault();
    setConnectorError(null);

    if (!connectorSpaceId) { setConnectorError("Select a space."); return; }
    if (!connectorType.trim()) { setConnectorError("Type is required."); return; }

    let configParsed: Record<string, unknown>;
    try {
      configParsed = JSON.parse(connectorConfig || "{}");
    } catch {
      setConnectorError("Config must be valid JSON.");
      return;
    }

    setConnectorSubmitting(true);
    try {
      const data = await api.post<{ connector: { id: string; type: string; schedule: string | null } }>(
        `/v1/spaces/${connectorSpaceId}/connectors`,
        { type: connectorType.trim(), config: configParsed, schedule: connectorSchedule.trim() || null }
      );
      setSessionConnectors((prev) => [...prev, { id: data.connector.id, type: data.connector.type, schedule: data.connector.schedule }]);
      setConnectorType("");
      setConnectorConfig("");
      setConnectorSchedule("");
    } catch (err: unknown) {
      setConnectorError(err instanceof Error ? err.message : "Failed to create connector.");
    } finally {
      setConnectorSubmitting(false);
    }
  };

  const handleSync = async (connectorId: string) => {
    setSyncErrors((prev) => ({ ...prev, [connectorId]: "" }));
    try {
      const data = await api.post<{ job_id: string }>(`/v1/connectors/${connectorId}/sync`, {});
      setSessionConnectors((prev) =>
        prev.map((c) => (c.id === connectorId ? { ...c, jobId: data.job_id } : c))
      );
    } catch (err: unknown) {
      setSyncErrors((prev) => ({ ...prev, [connectorId]: err instanceof Error ? err.message : "Sync failed." }));
    }
  };

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Connectors</h2>
      <p className="text-xs text-gray-400">Connectors created in previous sessions are not listed here.</p>

      <div className="bg-white rounded border p-5">
        <form onSubmit={handleCreateConnector} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <SpaceSelector spaces={spaces} selectedId={connectorSpaceId} onChange={setConnectorSpaceId} disabled={connectorSubmitting} />
          <input
            type="text"
            placeholder="Type (e.g. confluence)"
            value={connectorType}
            onChange={(e) => setConnectorType(e.target.value)}
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <textarea
            placeholder='Config JSON (e.g. {"base_url": "https://..."})'
            value={connectorConfig}
            onChange={(e) => setConnectorConfig(e.target.value)}
            rows={3}
            className="sm:col-span-2 border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            placeholder="Schedule (cron, optional)"
            value={connectorSchedule}
            onChange={(e) => setConnectorSchedule(e.target.value)}
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={connectorSubmitting}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {connectorSubmitting ? "Creating…" : "Create Connector"}
            </button>
            {connectorError && <p className="text-sm text-red-600">{connectorError}</p>}
          </div>
        </form>
      </div>

      {sessionConnectors.length > 0 && (
        <div className="bg-white rounded border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Type</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Schedule</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Action</th>
              </tr>
            </thead>
            <tbody>
              {sessionConnectors.map((c) => (
                <tr key={c.id} className="border-b">
                  <td className="px-4 py-2 font-mono text-xs">{c.type}</td>
                  <td className="px-4 py-2 text-gray-500">{c.schedule ?? "—"}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleSync(c.id)}
                        className="text-xs bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded"
                      >
                        Sync Now
                      </button>
                      {c.jobId && <span className="text-xs text-green-600 font-mono">Job: {c.jobId}</span>}
                      {syncErrors[c.id] && <span className="text-xs text-red-600">{syncErrors[c.id]}</span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// --- Agent Credentials Section ---

interface SessionCredential {
  id: string;
  name: string;
  max_confidentiality: string;
  revoked_at: string | null;
  token?: string;
}

function AgentCredentialsSection({ spaces }: { spaces: Space[] }) {
  const [credName, setCredName] = useState("");
  const [credSpaceIds, setCredSpaceIds] = useState<string[]>([]);
  const [credConfidentiality, setCredConfidentiality] = useState("internal");
  const [credError, setCredError] = useState<string | null>(null);
  const [credSubmitting, setCredSubmitting] = useState(false);
  const [sessionCreds, setSessionCreds] = useState<SessionCredential[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const toggleSpace = (id: string) => {
    setCredSpaceIds((prev) => prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]);
  };

  const handleCreateCredential = async (e: React.FormEvent) => {
    e.preventDefault();
    setCredError(null);

    if (!credName.trim()) { setCredError("Name is required."); return; }
    if (credSpaceIds.length === 0) { setCredError("Select at least one space."); return; }

    setCredSubmitting(true);
    try {
      const data = await api.post<{ credential: { id: string; name: string; max_confidentiality: string; revoked_at: string | null }; token: string }>(
        "/v1/agent-credentials",
        { name: credName.trim(), scoped_space_ids: credSpaceIds, max_confidentiality: credConfidentiality }
      );
      setSessionCreds((prev) => [...prev, { ...data.credential, token: data.token }]);
      setCredName("");
      setCredSpaceIds([]);
      setCredConfidentiality("internal");
    } catch (err: unknown) {
      setCredError(err instanceof Error ? err.message : "Failed to create credential.");
    } finally {
      setCredSubmitting(false);
    }
  };

  const handleRevoke = async (credId: string) => {
    try {
      await api.post(`/v1/agent-credentials/${credId}/revoke`, {});
      setSessionCreds((prev) =>
        prev.map((c) => (c.id === credId ? { ...c, revoked_at: new Date().toISOString(), token: undefined } : c))
      );
    } catch (err: unknown) {
      console.error(err);
    }
  };

  const copyToken = (token: string, credId: string) => {
    navigator.clipboard.writeText(token).then(() => {
      setCopiedId(credId);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Agent Credentials</h2>
      <p className="text-xs text-gray-400">Credentials created in previous sessions are not listed here.</p>

      <div className="bg-white rounded border p-5">
        <form onSubmit={handleCreateCredential} className="space-y-3">
          <input
            type="text"
            placeholder="Credential name (e.g. CI Agent)"
            value={credName}
            onChange={(e) => setCredName(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {spaces.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-gray-600">Scoped spaces (select at least one)</p>
              <div className="flex flex-wrap gap-2">
                {spaces.map((s) => (
                  <label key={s.id} className="flex items-center gap-1 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={credSpaceIds.includes(s.id)}
                      onChange={() => toggleSpace(s.id)}
                      className="rounded"
                    />
                    {s.name}
                  </label>
                ))}
              </div>
            </div>
          )}
          <select
            value={credConfidentiality}
            onChange={(e) => setCredConfidentiality(e.target.value)}
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="public">Public</option>
            <option value="internal">Internal</option>
            <option value="confidential">Confidential</option>
          </select>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={credSubmitting}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {credSubmitting ? "Creating…" : "Create Credential"}
            </button>
            {credError && <p className="text-sm text-red-600">{credError}</p>}
          </div>
        </form>
      </div>

      {sessionCreds.length > 0 && (
        <div className="space-y-3">
          {sessionCreds.map((c) => (
            <div key={c.id} className="bg-white rounded border p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{c.name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 capitalize">{c.max_confidentiality}</span>
                  {c.revoked_at ? (
                    <span className="text-xs text-red-500 font-medium">Revoked</span>
                  ) : (
                    <button
                      onClick={() => handleRevoke(c.id)}
                      className="text-xs bg-red-50 text-red-600 hover:bg-red-100 px-2 py-1 rounded"
                    >
                      Revoke
                    </button>
                  )}
                </div>
              </div>
              {c.token && !c.revoked_at && (
                <div className="bg-amber-50 border border-amber-200 rounded p-3 space-y-2">
                  <p className="text-xs font-semibold text-amber-800">⚠ This token will not be shown again. Copy it now.</p>
                  <div className="flex items-center gap-2">
                    <code className="text-xs font-mono bg-amber-100 px-2 py-1 rounded break-all flex-1">{c.token}</code>
                    <button
                      onClick={() => copyToken(c.token!, c.id)}
                      className="text-xs bg-amber-200 hover:bg-amber-300 px-2 py-1 rounded shrink-0"
                    >
                      {copiedId === c.id ? "Copied!" : "Copy"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
