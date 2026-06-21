<!--
SYNC IMPACT REPORT
==================
Version change: 1.2.0 → 1.3.0
Rationale: MINOR bump. Adds a new "UI Design System" section establishing the
canonical color palette (Slate + Indigo) and font stack (Geist/Inter). No Core
Principle is modified or removed; this only adds new mandatory UI guidance for
the frontend layer.

Prior amendment (v1.2.0): consolidated persistent storage onto PostgreSQL,
removing the Cassandra mandate.

Prior amendment (v1.1.0): expanded the caching rule to permit Redis/other
brokers as ephemeral task-queue transport.

Modified sections:
- None (existing sections unchanged).

Added sections:
- "UI Design System": color palette and typography standards for the frontend.

Removed sections:
- None.

Templates requiring updates:
- .specify/templates/plan-template.md ✅ no change needed (generic checks)
- .specify/templates/spec-template.md ✅ no change needed (no constitution refs)
- .specify/templates/tasks-template.md ✅ no change needed (no constitution refs)
- .specify/templates/checklist-template.md ✅ no change needed
- CLAUDE.md ✅ no change needed (generic plan-context guidance)

Follow-up TODOs:
- Existing components still using `blue-*` / `gray-*` Tailwind classes should
  be migrated to `indigo-*` / `slate-*` in a dedicated cleanup task.
-->

# Tessera Constitution

This constitution contains the non-negotiable principles governing all phases of
development for Tessera. Every specification (`spec.md`), engineering plan
(`plan.md`), and code implementation MUST validate against these rules. When a
principle conflicts with convenience, the principle wins.

## Core Principles

### I. Domain-Driven Architecture
Business logic MUST be modeled with Domain-Driven Design (DDD) and kept strictly
separated from infrastructure and framework code. Domain models MUST NOT import or
depend on framework, transport, or persistence libraries. Rationale: isolating the
domain keeps business rules testable and lets infrastructure evolve without
rewriting core logic.

### II. Separation of Concerns
Product definitions MUST remain agnostic of the underlying technologies that
implement them. A change of database, framework, or transport MUST NOT require a
change to product/domain definitions. Rationale: technology-agnostic boundaries
prevent vendor lock-in and contain the blast radius of infrastructure change.

### III. Data Locality & Consent
User data MUST NOT be persisted on a client machine without explicit, recorded
end-user authorization. Any local persistence path MUST document what is stored,
why, and how consent is captured. Rationale: protecting user data by default is a
privacy and compliance obligation, not an optional feature.

### IV. Test-Driven Development (NON-NEGOTIABLE)
Core business domains MUST be built test-first: write a failing test, confirm it
fails, then implement until it passes. Every code change MUST include companion
test coverage. Statement coverage MUST meet or exceed 85% across all Python
modules. Rationale: tests written before code define behavior unambiguously and
guard against regressions in the rules that matter most.

### V. Quality Gates
Code MUST pass Ruff and Black checks before being committed. Linting and formatting
violations MUST block the commit, not be deferred. Rationale: automated, uniform
quality gates remove style debate and keep the codebase consistently reviewable.

## Technical Stack Boundaries

* **Persistent storage**: PostgreSQL MUST be used as the single system of record for
  all persistent data, relational and non-relational alike — the latter via JSONB and
  extensions such as pgvector for vector data. Rationale: one authoritative store
  simplifies consistency, transactions, and auditability for the current scale.
* **Caching & message transport**: Redis MAY be used for session caching and as an
  ephemeral message broker or task-queue transport for asynchronous jobs. Other
  message brokers (e.g., RabbitMQ) MAY be used for the same purpose. Any store used
  for caching or brokering MUST NOT be treated as a system of record: durable,
  authoritative state MUST live in PostgreSQL (the system of record). Rationale:
  caches and brokers are ephemeral transport that can be
  flushed or rebuilt without data loss; keeping the system of record separate
  preserves durability and auditability.
* **Infrastructure as code**: All infrastructure MUST be declared as code using
  Docker containers and Kubernetes manifests. Manual, undeclared infrastructure
  changes are prohibited.

## UI Design System

All frontend work MUST conform to the following visual standards. Rationale: a
consistent palette prevents visual drift and gives Tessera a distinct identity
beyond the generic blue-gray SaaS default.

* **Color scale**: Tailwind's `slate-*` scale MUST be used for all neutral surfaces,
  borders, and text. The `gray-*` scale MUST NOT be introduced for new work.
* **Primary accent**: `indigo-600` MUST be used for interactive elements (buttons,
  links, focus rings). Hover states MUST use `indigo-700`; focus rings MUST use
  `indigo-500`. The `blue-*` scale MUST NOT be introduced for new work.
* **Semantic colors**: `red-*` remains the standard for error and destructive states.
  No other accent color families may be introduced without a constitution amendment.
* **Typography**: Geist Sans (primary) and Geist Mono (code) MUST be loaded as font
  variables; Inter from Google Fonts MAY be used as a body-text fallback. No other
  typefaces may be added without a constitution amendment.
* **Tone**: The UI MUST remain minimal and content-focused — subtle borders, generous
  whitespace, and no decorative gradients or heavy drop shadows on standard surfaces.

## Security Requirements

* **Authentication**: API gateways MUST authenticate using OAuth 2.0 with JSON Web
  Tokens (JWT).
* **Secret management**: Passwords, connection strings, and API keys MUST NOT be
  committed to source control. Secrets MUST be supplied via environment injection.
* **Audit logging**: Every state-changing action MUST emit a structured audit log
  recording the actor, timestamp, and affected entity ID.

## Documentation Separation

* **Product Specification (`spec.md`)**: MUST focus exclusively on WHAT and WHY. It
  MUST NOT reference frameworks, code patterns, or engineering jargon.
* **Engineering Plan (`plan.md`)**: MUST contain all technical decisions, package
  choices, database schemas, and the HOW of building each feature.

## Governance

This constitution supersedes all other development practices. Where any plan,
spec, or implementation conflicts with it, this document prevails.

* **Amendment procedure**: Amendments MUST be proposed as a documented change to
  this file, including rationale and a migration note for any affected artifacts.
  Changes take effect once merged.
* **Versioning policy**: This constitution is versioned with semantic versioning.
  MAJOR for backward-incompatible governance changes or principle removals/
  redefinitions; MINOR for a new principle/section or materially expanded guidance;
  PATCH for clarifications and non-semantic refinements.
* **Compliance review**: Every PR and review MUST verify compliance with these
  principles. Any complexity or deviation MUST be explicitly justified in the
  plan's Constitution Check, or the change MUST be revised to comply.
* **Runtime guidance**: Agents and contributors MUST consult the current `plan.md`
  for project-specific technical context, as directed by `CLAUDE.md`.

**Version**: 1.3.0 | **Ratified**: 2026-06-12 | **Last Amended**: 2026-06-20
