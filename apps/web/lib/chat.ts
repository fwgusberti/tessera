import { api } from "@/lib/api";
import type { AnswerResponse, HistoryMessage } from "@/lib/types";

export async function askAssistant(
  query: string,
  history: HistoryMessage[],
): Promise<AnswerResponse> {
  return api.post<AnswerResponse>("/v1/assistant/answer", { query, history });
}
