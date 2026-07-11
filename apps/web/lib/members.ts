import { api } from "./api";

export type SpaceRole = "admin" | "editor" | "viewer";

export interface MemberSpaceAccessRow {
  id: string;
  name: string;
  slug: string;
  parent_space_id: string | null;
  direct_role: SpaceRole | null;
  effective_role: SpaceRole | null;
  is_direct: boolean;
}

export interface MemberIdentity {
  user_id: string;
  display_name: string;
  email: string;
}

export interface MemberSpaceAccessResponse {
  member: MemberIdentity;
  spaces: MemberSpaceAccessRow[];
}

export async function getMemberSpaceAccess(
  userId: string
): Promise<MemberSpaceAccessResponse> {
  return api.get<MemberSpaceAccessResponse>(
    `/v1/companies/members/${userId}/space-access`
  );
}

export interface SpaceMembership {
  id: string;
  space_id: string;
  user_id: string;
  role: SpaceRole;
}

export async function addSpaceMember(
  spaceId: string,
  userId: string,
  role: SpaceRole
): Promise<SpaceMembership> {
  const res = await api.post<{ membership: SpaceMembership }>(
    `/v1/spaces/${spaceId}/members`,
    { user_id: userId, role }
  );
  return res.membership;
}

export async function changeSpaceMemberRole(
  spaceId: string,
  userId: string,
  role: SpaceRole
): Promise<SpaceMembership> {
  const res = await api.put<{ membership: SpaceMembership }>(
    `/v1/spaces/${spaceId}/members/${userId}`,
    { role }
  );
  return res.membership;
}

export async function removeSpaceMember(
  spaceId: string,
  userId: string
): Promise<void> {
  return api.delete<void>(`/v1/spaces/${spaceId}/members/${userId}`);
}
