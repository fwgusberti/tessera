# Data Model: AI-First Interface with Doc Access

## No new entities

This feature introduces no new database tables, domain entities, or persistent storage. All changes are:

1. An extension to an existing data transfer object (Citation)
2. UI additions to an existing component (NavBar, MessageBubble)

---

## Modified DTO: Citation

**Current shape** (`apps/web/lib/types.ts`):
```ts
export interface Citation {
  chunk_id: string;
  document_version_id: string;
  quote: string;
  score: number;
}
```

**Extended shape** (this feature):
```ts
export interface Citation {
  chunk_id: string;
  document_id: string;           // NEW — used to build /documents/{id} link
  document_version_id: string;
  quote: string;
  score: number;
}
```

**Corresponding backend change** (`apps/api/tessera_api/rag/citations.py`):

```python
def build_citation(chunk_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": str(chunk_row["id"]),
        "document_id": str(chunk_row["document_id"]),   # NEW
        "document_version_id": str(chunk_row["document_version_id"]),
        "quote": chunk_row["text"][:200],
        "score": float(chunk_row.get("score", 0.0)),
    }
```

`document_id` is already present in every raw chunk row returned by `acl_first_search` (it is a column on the chunk table). No migration, no new query is required.

---

## UI Entities (no persistence)

### Navigation Control

A pair of named links rendered in `NavBar`:

| Label | Destination | Active when |
|-------|------------|-------------|
| Chat | `/` | `pathname === "/"` |
| Documents | `/documents` | `pathname.startsWith("/documents")` |

These are visual elements only; they carry no state beyond what `usePathname` provides.

### Document Reference (citation link)

Rendered in `MessageBubble` for each `citation` in a completed, non-dont_know `ChatTurn`:

| Field | Source | Used for |
|-------|--------|---------|
| `document_id` | `citation.document_id` | URL `/documents/{id}` |
| `quote` | `citation.quote` | Link label (truncated) |

Links open in `target="_blank" rel="noopener noreferrer"` to preserve chat state.
