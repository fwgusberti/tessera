export interface Space {
  id: string;
  slug: string;
  name: string;
  sector: string;
  default_language: string;
  confidence_threshold: number;
  retention_policy: Record<string, unknown>;
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

export interface AuthUser {
  id: string;
  email: string;
  isAdmin: boolean;
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
}

export type RefreshResponse = LoginResponse;

export interface RegisterCredentials {
  displayName: string;
  email: string;
  password: string;
}

export type PasswordStrength = "weak" | "medium" | "strong";
