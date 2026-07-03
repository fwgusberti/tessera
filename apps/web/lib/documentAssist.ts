import { api } from "@/lib/api";
import type { DraftAssistResponse, RevisionAssistResponse } from "@/lib/types";

export async function generateDraft(
  spaceId: string,
  prompt: string,
  previousSuggestion?: string,
): Promise<DraftAssistResponse> {
  return api.post<DraftAssistResponse>("/v1/documents/assist/draft", {
    space_id: spaceId,
    prompt,
    previous_suggestion: previousSuggestion,
  });
}

export async function reviseContent(
  documentId: string,
  content: string,
  instruction: string,
  previousSuggestion?: string,
): Promise<RevisionAssistResponse> {
  return api.post<RevisionAssistResponse>(`/v1/documents/${documentId}/assist/revise`, {
    content,
    instruction,
    previous_suggestion: previousSuggestion,
  });
}
