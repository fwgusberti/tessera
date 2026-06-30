# Data Model: Frontend Spaces Page

This feature is read-only on the frontend. No new backend entities or database tables are introduced. The relevant domain entities already exist.

## Entities Consumed from the API

### Space

Already defined in `apps/web/lib/types.ts` as:

```typescript
interface Space {
  id: string;
  slug: string;
  name: string;
  sector: string;
  default_language: string;
  confidence_threshold: number;
  retention_policy: Record<string, unknown>;
}
```

Fields displayed on the listing: `id` (for navigation), `name`, `sector`.

### SpaceMembership (my membership)

Not yet in `apps/web/lib/types.ts`. Must be added:

```typescript
type SpaceRole = "admin" | "editor" | "viewer";

interface MySpaceMembership {
  space_id: string;
  user_id: string;
  role: SpaceRole;
  created_at: string;
}
```

Field displayed on each card: `role` (via the existing `RoleBadge` component).

## Client-Side State Model

The `SpacesPage` component manages:

```typescript
interface SpaceWithRole {
  space: Space;
  role: SpaceRole | null;  // null = not a member or fetch failed
}

// Component state:
const [items, setItems] = useState<SpaceWithRole[]>([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
```

**State transitions**:
1. Mount → `loading = true`
2. `GET /v1/spaces` settles → parallel role fetches start
3. All role fetches settle → `items` populated, `loading = false`
4. If `/v1/spaces` fails → `error` set, `loading = false`
5. If individual role fetch fails → `role: null` for that space (non-fatal)

## Sorting

Spaces sorted client-side: `items.sort((a, b) => a.space.name.localeCompare(b.space.name))` before rendering.

## No New Persistence

No localStorage, cookies, or IndexedDB usage. Token handling is already managed by the existing `api` client and `useAuth` hook.
