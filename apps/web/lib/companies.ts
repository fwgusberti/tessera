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

export interface CompanyProfile {
  id: string;
  name: string;
  industry: string | null;
  team_size: string | null;
  created_at: string; // ISO 8601
  role: "admin" | "member"; // caller's role in this company
}

export interface UpdateCompanyData {
  name: string;
  industry: string | null;
  team_size: string | null;
}

export async function getCurrentCompany(): Promise<CompanyProfile> {
  return api.get<CompanyProfile>("/v1/companies/current");
}

export async function updateCurrentCompany(data: UpdateCompanyData): Promise<CompanyProfile> {
  return api.patch<CompanyProfile>("/v1/companies/current", data);
}

export interface CompanyMember {
  user_id: string;
  display_name: string;
  email: string;
  role: "admin" | "member";
}

export async function getCompanyMembers(): Promise<CompanyMember[]> {
  const res = await api.get<{ members: CompanyMember[] }>("/v1/companies/members");
  return res.members;
}

export type CompanyRole = "admin" | "member";

export interface InviteCompanyMemberResponse {
  status: "sent";
  email: string;
  role: CompanyRole;
}

export async function inviteCompanyMember(
  email: string,
  role: CompanyRole
): Promise<InviteCompanyMemberResponse> {
  return api.post<InviteCompanyMemberResponse>("/v1/companies/invitations", { email, role });
}

export interface AddableUser {
  user_id: string;
  display_name: string;
  email: string;
}

export async function searchAddableUsers(q: string): Promise<AddableUser[]> {
  const res = await api.get<{ users: AddableUser[] }>(
    `/v1/companies/addable-users?q=${encodeURIComponent(q)}`
  );
  return res.users;
}

export async function addCompanyMember(
  userId: string,
  role: CompanyRole
): Promise<CompanyMember> {
  const res = await api.post<{ member: CompanyMember }>("/v1/companies/members", {
    user_id: userId,
    role,
  });
  return res.member;
}
