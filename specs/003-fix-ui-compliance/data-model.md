# Data Model: UI Compliance with Implemented Functionality

**Date**: 2026-06-12
**Source**: Derived from existing API response shapes (routers) and domain entities.

This document records the TypeScript types used by the web UI to represent API responses.
No new backend entities are introduced. All shapes come from the existing backend.

---

## Core Types

### Space

```typescript
interface Space {
  id: string;                // UUID
  slug: string;              // URL-safe identifier (e.g., "engineering")
  name: string;              // Display name
  sector: string;            // Business sector
  default_language: string;  // BCP-47 language code (e.g., "pt-BR")
  confidence_threshold: number; // 0.0–1.0
  retention_policy: Record<string, unknown>;
}
```

### Document

```typescript
interface Document {
  id: string;                // UUID
  space_id: string;          // UUID — owning space
  title: string;
  language: string;
  confidentiality: "public" | "internal" | "confidential" | "restricted";
  tags: string[];
  state: "ingested" | "published" | "archived";
  current_version_id: string | null; // UUID or null
  owner_user_id: string | null;
  created_at: string;        // ISO 8601
  updated_at: string;        // ISO 8601
}
```

### DocumentVersion

```typescript
interface DocumentVersion {
  id: string;                // UUID
  document_id: string;       // UUID
  version_number: number;
  content_markdown: string;
  frontmatter: Record<string, unknown>;
  approver_user_id: string | null;
  approved_at: string | null; // ISO 8601
  created_from_proposal_id: string | null;
  created_at: string;
}
```

### Proposal

```typescript
interface Proposal {
  id: string;                // UUID
  document_id: string;       // UUID
  state: "pending" | "approved" | "rejected";
  summary: string | null;
  drift_score: number | null; // 0.0–1.0
  proposed_markdown_patch: string;
  rejection_reason: string | null;
  created_at: string;
}
```

### Connector

```typescript
interface Connector {
  id: string;                // UUID
  space_id: string;          // UUID
  type: string;              // e.g., "confluence", "notion", "github"
  config: Record<string, unknown>;
  schedule: string | null;   // cron expression or null
  created_at: string;
}
```

### Metrics

```typescript
interface Metrics {
  correct_answer_rate: number | null;
  dont_know_rate: number | null;
  documents_with_drift: number;
  time_to_approval_p50: number | null; // hours
  time_to_approval_p90: number | null; // hours
  total_queries: number;
}
```

### AgentCredential

```typescript
interface AgentCredential {
  id: string;                // UUID
  name: string;
  scoped_space_ids: string[]; // UUID[]
  max_confidentiality: "public" | "internal" | "confidential" | "restricted";
  revoked_at: string | null;
  created_at: string;
}
```

---

## API Response Envelopes

All endpoints return JSON objects with a typed key:

| Endpoint | Response Shape |
|---|---|
| `GET /v1/spaces` | `{ spaces: Space[] }` |
| `POST /v1/spaces` | `{ space: Space }` |
| `POST /v1/spaces/{id}/permissions` | `{ permission: RolePermission }` |
| `POST /v1/spaces/{id}/connectors` | `{ connector: Connector }` |
| `POST /v1/connectors/{id}/sync` | `{ job_id: string }` |
| `GET /v1/documents?space_id=&state=` | `{ documents: Document[] }` |
| `GET /v1/documents/{id}` | `{ document: Document, current_version: DocumentVersion \| null }` |
| `GET /v1/documents/{id}/versions` | `{ versions: DocumentVersion[] }` |
| `POST /v1/documents/{id}/publish` | `{ document: Document, version: DocumentVersion }` |
| `GET /v1/metrics` | `Metrics` (flat, no envelope) |
| `POST /v1/agent-credentials` | `{ credential: AgentCredential, token: string }` |
| `POST /v1/agent-credentials/{id}/revoke` | `{ credential: AgentCredential }` |
| `GET /v1/admin/spaces` | `{ spaces: Space[] }` |

---

## State Transitions

### Document Lifecycle

```
ingested → published
published → archived  (future, not in scope)
```

The "Publish" button is shown only when `document.state === "ingested"` and the backend enforces the transition.

### Proposal Lifecycle

```
pending → approved
pending → rejected
```

Already handled by the existing proposals page. No changes to this flow.

---

## Relationships

- A **Space** contains many **Documents**.
- A **Document** has many **DocumentVersions** (ordered by `version_number`).
- A **Document** has a `current_version_id` pointing to the active version.
- A **Space** can have many **Connectors**.
- A **Connector** triggers ingestion jobs that produce **Documents**.
- A **Proposal** references exactly one **Document**.
