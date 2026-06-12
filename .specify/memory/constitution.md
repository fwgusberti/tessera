<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 1.2.0
Rationale: MINOR bump. Removes the Cassandra mandate from Technical Stack Boundaries
and consolidates persistent storage onto PostgreSQL (relational + non-relational via
JSONB and extensions such as pgvector). Classified MINOR, not MAJOR: this relaxes a
supporting stack rule (not a Core Principle I–V) and is backward-compatible for all
downstream artifacts — it only widens what is permitted. (A stricter reading of
"removals = MAJOR" would make this 2.0.0; chosen MINOR for consistency with the
v1.1.0 Redis relaxation and because no Core Principle is removed.)

Prior amendment (v1.1.0): expanded the caching rule to permit Redis/other brokers as
ephemeral task-queue transport (caches/brokers still MUST NOT be a system of record).

Modified sections:
- "Technical Stack Boundaries": removed the "Non-relational storage: Cassandra"
  bullet; "Relational storage" → "Persistent storage" (PostgreSQL as the single
  system of record for relational and non-relational data). Caching bullet's
  durable-state reference updated to drop Cassandra.

Added sections:
- None.

Removed sections:
- "Non-relational storage" stack bullet (Cassandra mandate).

Templates requiring updates:
- .specify/templates/plan-template.md ✅ no change needed (generic "Constitution Check")
- .specify/templates/spec-template.md ✅ no change needed (no constitution refs)
- .specify/templates/tasks-template.md ✅ no change needed (no constitution refs)
- .specify/templates/checklist-template.md ✅ no change needed
- CLAUDE.md ✅ no change needed (generic plan-context guidance)

Follow-up TODOs:
- specs/001-living-docs-platform/plan.md: the Redis-as-broker AND Cassandra entries
  in Complexity Tracking are now compliant (v1.2.0) and may be removed (manual).
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

**Version**: 1.2.0 | **Ratified**: 2026-06-12 | **Last Amended**: 2026-06-12
