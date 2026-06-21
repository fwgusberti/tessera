"use client";

interface Step {
  id: string;
  label: string;
}

const STEPS: Step[] = [
  { id: "profile", label: "Profile" },
  { id: "company", label: "Company" },
  { id: "invite", label: "Invite" },
  { id: "complete", label: "Done" },
];

interface ProgressStepperProps {
  currentStep: string;
  completedSteps: string[];
}

export function ProgressStepper({ currentStep, completedSteps }: ProgressStepperProps) {
  return (
    <nav aria-label="Onboarding progress">
      <ol className="flex items-center space-x-2">
        {STEPS.map((step, index) => {
          const isCompleted = completedSteps.includes(step.id);
          const isCurrent = step.id === currentStep;
          const isPending = !isCompleted && !isCurrent;

          return (
            <li key={step.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={[
                    "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
                    isCompleted
                      ? "bg-indigo-600 text-white"
                      : isCurrent
                        ? "bg-indigo-100 text-indigo-700 border-2 border-indigo-600"
                        : "bg-slate-100 text-slate-400",
                  ].join(" ")}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  {isCompleted ? (
                    <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                <span
                  className={[
                    "mt-1 text-[10px] sm:text-xs",
                    isCurrent ? "text-indigo-700 font-medium" : isPending ? "text-slate-400" : "text-indigo-600",
                  ].join(" ")}
                >
                  {step.label}
                </span>
              </div>
              {index < STEPS.length - 1 && (
                <div
                  className={[
                    "w-6 sm:w-12 h-0.5 mx-1 sm:mx-2 mb-5",
                    isCompleted ? "bg-indigo-600" : "bg-slate-200",
                  ].join(" ")}
                  aria-hidden
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
