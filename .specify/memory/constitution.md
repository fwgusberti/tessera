<!--
SYNC IMPACT REPORT
==================
Version change: 1.3.0 → 1.4.0
Rationale: MINOR bump. Adds a new Core Principle VI ("Tenant Data Isolation")
and expands the Security Requirements section with explicit multi-tenancy
enforcement rules. The bug that prompted this amendment: companies were
accessing each other's Spaces because no architectural principle mandated
per-tenant query scoping. No existing principle is renamed or removed.

Prior amendment (v1.3.0): added UI Design System section (color palette +
typography standards).

Prior amendment (v1.2.0): consolidated persistent storage onto PostgreSQL.

Prior amendment (v1.1.0): expanded caching rule to permit Redis/other brokers
as ephemeral task-queue transport.

Modified sections:
- "Security Requirements": added Tenant Data Isolation subsection with
  enforcement rules for multi-tenancy.

Added sections:
- Core Principle VI: Tenant Data Isolation (new non-negotiable principle).

Removed sections:
- None.

Templates requiring updates:
- .specify/templates/plan-template.md ✅ no change needed — Constitution Check
  is generic and picks up the new principle automatically.
- .specify/templates/spec-template.md ✅ no change needed — no constitution
  refs hardcoded.
- .specify/templates/tasks-template.md ✅ no change needed — task categories
  are project-driven, not principle-enumerated.
- .specify/templates/checklist-template.md ✅ no change needed.
- CLAUDE.md ✅ no change needed (generic plan-context guidance).

Follow-up TODOs:
- Existing data-access layers (Space, Document, Chat) MUST be audited for
  missing company_id scoping and any violations fixed before the next release.
- Row-Level Security (RLS) policies on the PostgreSQL side should be
  evaluated as a defense-in-depth enforcement layer.
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

### VI. Tenant Data Isolation (NON-NEGOTIABLE)
Every data access MUST be strictly scoped to the authenticated company (tenant).
Cross-tenant data leakage — reading, writing, or referencing another company's
data without explicit, audited authorization — is a critical security violation.

Concrete rules:

* Every database query and mutation MUST include an explicit `company_id` filter
  derived from the authenticated session. Unscoped queries on multi-tenant tables
  are PROHIBITED.
* Company context MUST be established at the request boundary (API layer) and
  MUST be propagated unchanged through every service, repository, and persistence
  call in that request's call chain. It MUST NOT be re-derived from user-supplied
  input deeper in the stack.
* No service or repository method that returns tenant-owned data may accept a
  bare entity ID without also receiving and validating the `company_id`. Methods
  that omit tenant scoping MUST be rejected in code review.
* Cross-tenant access is permitted ONLY for explicitly modeled, audited operations
  (e.g., a super-admin read that is separately role-gated and audit-logged). Any
  such operation MUST be documented in the plan and flagged in the Constitution
  Check.
* Automated isolation tests MUST be written for every data-access path: a request
  authenticated as Company A attempting to access Company B's resources MUST
  receive a 403 or empty result — never Company B's data.

Rationale: in a multi-tenant SaaS, a single missing `company_id` predicate is a
data breach. The principle must be enforced architecturally and verified by tests,
not left to developer discipline on each feature.

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
* **Tenant data isolation**: See Core Principle VI. Every feature plan MUST include
  an explicit "Tenant Isolation" section in its Constitution Check, identifying which
  tables are accessed, confirming `company_id` scoping is present on every query, and
  listing the cross-tenant isolation tests that will be written. Features that omit
  this check MUST NOT be merged.

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

**Version**: 1.4.0 | **Ratified**: 2026-06-12 | **Last Amended**: 2026-06-22
