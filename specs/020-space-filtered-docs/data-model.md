# Data Model: Space-Filtered Document Listing

No new database tables or migrations are required. This feature works entirely with existing entities and the current schema.

## Existing Entities Involved

### User
| Field | Type | Relevance |
|-------|------|-----------|
| `id` | UUID | Used to identify the requesting user |
| `external_subject` | str | Used to look up user from JWT `sub` claim |
| `is_admin` | bool | When `True`, bypasses group-based space filtering |
| `groups` | `list[str]` | IDP group names; matched against `RolePermission.idp_group` |

### RolePermission
| Field | Type | Relevance |
|-------|------|-----------|
| `space_id` | UUID | Links the permission to a space |
| `idp_group` | str | Group that holds the role in this space |
| `role` | UserRole | Not used for "can access space" — any role grants visibility |
| `max_confidentiality` | Confidentiality | Not used for space list — document-level filtering applies separately |

### Space
| Field | Type | Relevance |
|-------|------|-----------|
| `id` | UUID | Used as filter in document queries |
| `name` | str | Displayed in the space selector |

### Document
| Field | Type | Relevance |
|-------|------|-----------|
| `space_id` | UUID | Key join field for multi-space fetch |
| `state` | DocumentLifecycleState | Optional filter passed through from caller |

## Access Rule (no change to domain)

A user can see a space's documents if:
- `user.is_admin == True` → access to all spaces, OR
- There exists a `RolePermission` record where `rp.space_id == space.id` AND `rp.idp_group ∈ user.groups`

This rule is already captured in `tessera_core/permissions/access.py:resolve_user_role()`. The new SQL implementation in `SqlSpaceRepository.list_for_user()` implements it at the DB level for efficiency.

## Port Contract Change

A new abstract method is added to `DocumentRepository` (in `tessera_core/ports/repositories.py`):

```python
@abstractmethod
async def list_by_space_ids(
    self,
    space_ids: list[UUID],
    state: DocumentLifecycleState | None = None,
) -> list[Document]: ...
```

**Validation rules**:
- `space_ids = []` → returns `[]` without querying the DB (user has no accessible spaces)
- `state` is optional; when provided, adds a state filter to the query

## No State Transitions

This feature is read-only. No lifecycle state changes to any entity.
