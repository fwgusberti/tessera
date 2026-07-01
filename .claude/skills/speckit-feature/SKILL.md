---
name: "speckit-feature"
description: "Run the full speckit workflow end-to-end: specify → clarify → plan → tasks → analyze → implement. Use when the user wants to go from a feature description all the way to a working implementation in one shot. Triggers on phrases like 'implement feature', 'build this feature', 'full speckit', 'spec and implement', or any request that describes a feature and wants it fully developed without manual steps in between."
argument-hint: "Describe the feature you want to specify, plan, and implement"
compatibility: "Requires spec-kit project structure with .specify/ directory"
user-invocable: true
---

## User Input

```text
$ARGUMENTS
```

## What This Skill Does

Runs the six core speckit phases in sequence, passing the user's feature description to `speckit-specify` and then chaining through clarify, plan, tasks, analyze, and implement automatically.

## Execution Steps

Execute each step in order. Do NOT proceed to the next step until the current one has fully completed.

### Step 1 — Specify

Invoke the `speckit-specify` skill, passing the full contents of the **User Input** block above as the argument. Wait for it to complete before continuing.

### Step 2 — Plan

Invoke the `speckit-plan` skill with no arguments. Wait for it to complete before continuing.

### Step 3 — Update Agent Context

Invoke the `speckit-agent-context-update` skill with no arguments. This refreshes the coding agent context file (e.g. `CLAUDE.md`) so it points at the newly created plan. Wait for it to complete before continuing.

### Step 4 — Tasks

Invoke the `speckit-tasks` skill with no arguments. Wait for it to complete before continuing.

### Step 5 — Implement

Invoke the `speckit-implement` skill with no arguments. Wait for it to complete.

## Done

When all phases finish, report a brief rollup:
- Spec path and feature name
- Plan phases and key architectural decisions
- Number of tasks generated and coverage percentage (from the analyze report)
- Any issues flagged by analyze that were deferred to post-implementation
- One sentence on what was implemented
