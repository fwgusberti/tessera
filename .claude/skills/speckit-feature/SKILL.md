---
name: "speckit-feature"
description: "Run the full speckit workflow end-to-end: specify → plan → tasks → implement. Use when the user wants to go from a feature description all the way to a working implementation in one shot. Triggers on phrases like 'implement feature', 'build this feature', 'full speckit', 'spec and implement', or any request that describes a feature and wants it fully developed without manual steps in between."
argument-hint: "Describe the feature you want to specify, plan, and implement"
compatibility: "Requires spec-kit project structure with .specify/ directory"
user-invocable: true
---

## User Input

```text
$ARGUMENTS
```

## What This Skill Does

Runs the four core speckit phases in sequence, passing the user's feature description to `speckit-specify` and then chaining through plan, tasks, and implement automatically.

## Execution Steps

Execute each step in order. Do NOT proceed to the next step until the current one has fully completed.

### Step 1 — Specify

Invoke the `speckit-specify` skill, passing the full contents of the **User Input** block above as the argument. Wait for it to complete before continuing.

### Step 2 — Plan

Invoke the `speckit-plan` skill with no arguments. Wait for it to complete before continuing.

### Step 3 — Tasks

Invoke the `speckit-tasks` skill with no arguments. Wait for it to complete before continuing.

### Step 4 — Implement

Invoke the `speckit-implement` skill with no arguments. Wait for it to complete.

## Done

When all four phases finish, summarize what was implemented in one or two sentences.
