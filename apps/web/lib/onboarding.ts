import { api } from "./api";

export interface OnboardingStatus {
  completed: boolean;
  current_step: string;
  completed_steps: string[];
  company_join_method: "created" | "joined" | null;
}

export interface ProfileData {
  full_name: string;
  title?: string;
}

export interface StepAdvanceResponse {
  current_step: string;
  completed_steps: string[];
}

export interface CompleteResponse {
  completed: boolean;
  completed_at: string;
}

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  return api.get<OnboardingStatus>("/v1/onboarding/status");
}

export async function saveProfile(data: ProfileData): Promise<StepAdvanceResponse> {
  return api.post<StepAdvanceResponse>("/v1/onboarding/profile", data);
}

export async function completeOnboarding(): Promise<CompleteResponse> {
  return api.post<CompleteResponse>("/v1/onboarding/complete", {});
}
