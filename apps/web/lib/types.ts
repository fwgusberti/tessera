export type SpaceRole = "admin" | "editor" | "viewer";

export interface MySpaceMembership {
  space_id: string;
  user_id: string;
  role: SpaceRole;
  created_at: string;
}

export interface SpaceWithRole {
  space: Space;
  role: SpaceRole | null;
}

export interface Space {
  id: string;
  slug: string;
  name: string;
  sector: string;
  parent_space_id: string | null;
  default_language: string;
  confidence_threshold: number;
  retention_policy: Record<string, unknown>;
}

export interface SpaceAccess {
  space: Space;
  effective_role: SpaceRole;
  is_direct: boolean;
}

export interface Ancestor {
  id: string;
  name: string;
  slug: string;
}

export interface CompanyMemberMatch {
  user_id: string;
  display_name: string;
  email: string;
}

export interface Document {
  id: string;
  space_id: string;
  title: string;
  language: string;
  confidentiality: "public" | "internal" | "confidential" | "restricted";
  tags: string[];
  state: "ingested" | "published" | "archived";
  current_version_id: string | null;
  owner_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  content_markdown: string;
  frontmatter: Record<string, unknown>;
  approver_user_id: string | null;
  approved_at: string | null;
  created_from_proposal_id: string | null;
  created_at: string;
}

export interface DocumentDraft {
  content_markdown: string;
  editor_user_id: string;
  started_at: string;
  last_autosaved_at: string;
}

export interface Connector {
  id: string;
  space_id: string;
  type: string;
  config: Record<string, unknown>;
  schedule: string | null;
  created_at: string;
}

export interface Metrics {
  correct_answer_rate: number | null;
  dont_know_rate: number | null;
  documents_with_drift: number;
  time_to_approval_p50: number | null;
  time_to_approval_p90: number | null;
  total_queries: number;
}

export interface AgentCredential {
  id: string;
  name: string;
  scoped_space_ids: string[];
  max_confidentiality: "public" | "internal" | "confidential" | "restricted";
  revoked_at: string | null;
  created_at: string;
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export type TokenKind = "full" | "select" | "onboarding";

export interface AuthUser {
  id: string;
  email: string;
  isAdmin: boolean;
  tokenKind: TokenKind;
  companyId: string | null;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  tenant_selection_required?: boolean;
}

export type RefreshResponse = LoginResponse;

export interface RegisterCredentials {
  displayName: string;
  email: string;
  password: string;
}

export type PasswordStrength = "weak" | "medium" | "strong";

// ─── Chat / Assistant ─────────────────────────────────────────────────────────

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_version_id: string;
  quote: string;
  score: number;
}

export interface AnswerResponse {
  answer: string | null;
  citations?: Citation[];
  confidence: number;
  dont_know?: boolean;
  suggested_owner?: { space_name: string };
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatTurn {
  id: string;
  question: string;
  answer: AnswerResponse | null;
  status: "pending" | "complete" | "error";
  errorMessage?: string;
}

// ─── AI Document Assistance ────────────────────────────────────────────────────

export interface DraftAssistRequest {
  space_id: string;
  prompt: string;
  previous_suggestion?: string;
}

export interface DraftAssistResponse {
  content_markdown: string;
}

export interface RevisionAssistRequest {
  content: string;
  instruction: string;
  previous_suggestion?: string;
}

export interface RevisionAssistResponse {
  suggestion: string;
}
