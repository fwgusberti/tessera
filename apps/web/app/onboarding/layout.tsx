"use client";

import { useEffect, useState } from "react";
import { ProgressStepper } from "@/components/onboarding/ProgressStepper";
import { getOnboardingStatus } from "@/lib/onboarding";

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  const [currentStep, setCurrentStep] = useState("profile");
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);

  useEffect(() => {
    getOnboardingStatus()
      .then((status) => {
        setCurrentStep(status.current_step);
        setCompletedSteps(status.completed_steps);
      })
      .catch(() => {
        // If API call fails, start at profile
      });
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-start pt-12 px-4">
      <div className="w-full max-w-lg">
        <div className="mb-8 flex flex-col items-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Welcome to Tessera</h1>
          <p className="text-slate-500 text-sm mb-6">Let&apos;s get you set up in just a few steps.</p>
          <ProgressStepper currentStep={currentStep} completedSteps={completedSteps} />
        </div>
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 sm:p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
