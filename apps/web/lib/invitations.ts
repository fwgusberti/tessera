import { api } from "./api";

export interface FailedInvitation {
  email: string;
  reason: string;
}

export interface InvitationResult {
  sent: string[];
  failed: FailedInvitation[];
}

export async function sendInvitations(emails: string[]): Promise<InvitationResult> {
  return api.post<InvitationResult>("/v1/invitations", { emails });
}
