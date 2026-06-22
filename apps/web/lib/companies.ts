import { api } from "./api";

export interface CompanySuggestionInvitation {
  id: string;
  company_id: string;
  company_name: string;
  invited_by: string;
  expires_at: string;
}

export interface CompanySuggestionDomainMatch {
  company_id: string;
  company_name: string;
  domain: string;
  policy: "auto_join" | "request_approval";
}

export interface CompanySuggestions {
  invitations: CompanySuggestionInvitation[];
  domain_matches: CompanySuggestionDomainMatch[];
}

export interface CreateCompanyData {
  name: string;
  industry?: string;
  team_size?: string;
}

export interface CreateCompanyResponse {
  id: string;
  name: string;
  industry: string | null;
  team_size: string | null;
  role: string;
  created_at: string;
}

export interface JoinCompanyResponse {
  status: "joined" | "pending";
  company_id: string;
  company_name: string;
  role?: string;
}

export interface JoinStatusResponse {
  status: "pending" | "approved" | "denied";
  company_name: string;
  requested_at?: string;
  approved_at?: string;
}

export async function getSuggestions(): Promise<CompanySuggestions> {
  return api.get<CompanySuggestions>("/v1/companies/suggestions");
}

export async function createCompany(data: CreateCompanyData): Promise<CreateCompanyResponse> {
  return api.post<CreateCompanyResponse>("/v1/companies", data);
}

export async function joinCompany(
  companyId: string,
  method: "invitation",
  invitationId: string
): Promise<JoinCompanyResponse>;
export async function joinCompany(
  companyId: string,
  method: "domain_match"
): Promise<JoinCompanyResponse>;
export async function joinCompany(
  companyId: string,
  method: "invitation" | "domain_match",
  invitationId?: string
): Promise<JoinCompanyResponse> {
  return api.post<JoinCompanyResponse>(`/v1/companies/${companyId}/join`, {
    method,
    ...(invitationId ? { invitation_id: invitationId } : {}),
  });
}

export async function getJoinStatus(companyId: string): Promise<JoinStatusResponse> {
  return api.get<JoinStatusResponse>(`/v1/companies/${companyId}/join-status`);
}

export async function cancelJoinRequest(companyId: string): Promise<void> {
  return api.delete<void>(`/v1/companies/${companyId}/join-request`);
}

export interface CompanyEntry {
  id: string;
  name: string;
  role: "admin" | "member";
}

export interface CompanyMeResponse {
  companies: CompanyEntry[];
}

export async function getMyCompanies(): Promise<CompanyEntry[]> {
  const res = await api.get<CompanyMeResponse>("/v1/companies/me");
  return res.companies;
}
