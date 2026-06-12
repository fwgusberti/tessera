---

description: "Task list for Tessera — Plataforma de Documentação Viva"
---

# Tasks: Plataforma de Documentação Viva (Tessera)

**Input**: Design documents from `/specs/001-living-docs-platform/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED. The constitution mandates TDD (NON-NEGOTIABLE, ≥85% statement coverage) and the plan requests pytest, contract tests for connectors/MCP, and adversarial permission tests. Test tasks are written FIRST and must FAIL before implementation. Permissions and drift modules get the highest-priority coverage.

**Organization**: Tasks grouped by user story (P1→P3) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 mapping to spec.md user stories
- Exact file paths included per the monorepo structure in plan.md

## Path Conventions (from plan.md)

- Shared domain: `packages/core/tessera_core/`, tests `packages/core/tests/`
- Backend API: `apps/api/tessera_api/`, tests `apps/api/tests/`
- MCP server: `apps/mcp-server/tessera_mcp/`, tests `apps/mcp-server/tests/`
- Workers (Celery, connectors, drift): `apps/workers/tessera_workers/`, tests `apps/workers/tests/`
- Frontend: `apps/web/`
- Migrations: `db/migrations/`; deploy: `deploy/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and tooling

- [X] T001 Create monorepo structure per plan.md (`packages/core`, `apps/api`, `apps/mcp-server`, `apps/workers`, `apps/web`, `db/migrations`, `deploy`)
- [X] T002 [P] Initialize Python 3.12 packages (core, api, mcp-server, workers) with `pyproject.toml` and deps: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Celery, `anthropic`, Voyage client, MCP Python SDK, Authlib, OpenTelemetry
- [X] T003 [P] Initialize Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui in `apps/web/`
- [X] T004 [P] Configure Ruff + Black + pre-commit hooks (quality gate that blocks commits) at repo root
- [X] T005 [P] Configure pytest + pytest-cov with `--cov-fail-under=85` in `pyproject.toml`/`pytest.ini`
- [X] T006 [P] Configure Vitest + Testing Library in `apps/web/`
- [X] T007 Author `deploy/docker-compose.yml` (postgres+pgvector, redis, api, worker, mcp, web) and per-app `deploy/Dockerfile.*`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain, permissions, auth, schema, and seams that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Setup Alembic migrations framework and enable the `pgvector` extension in `db/migrations/`
- [X] T009 [P] Define framework-free domain entities (Space, Document, DocumentVersion, Chunk, Connector, SourceArtifact, UpdateProposal, User, Group/RolePermission, AgentCredential, AuditRecord, Citation) in `packages/core/tessera_core/domain/`
- [X] T010 [P] Define ports/interfaces (`LLMProvider`, `EmbeddingProvider`, `Connector`, repository protocols) in `packages/core/tessera_core/ports/`
- [X] T011 [P] Write FAILING unit tests for the access-decision function (RBAC by space + confidentiality, restricted exclusion) in `packages/core/tests/test_permissions.py`
- [X] T012 Implement `core.permissions` access-decision engine in `packages/core/tessera_core/permissions/` (make T011 pass)
- [X] T013 Implement document lifecycle state machine (Ingerido→Sem dono→Publicado→Desatualizado→Expirado) with FAILING-first tests in `packages/core/tessera_core/services/lifecycle.py` and `packages/core/tests/test_lifecycle.py`
- [X] T014 Implement SQLAlchemy models and the initial migration for all entities (incl. `Chunk.embedding` vector column with HNSW index) in `apps/api/tessera_api/adapters/models.py` and `db/migrations/`
- [X] T015 [P] Implement OIDC (Google Workspace) auth, session, and group→sector/role resolution in `apps/api/tessera_api/auth/`
- [X] T016 [P] Implement base FastAPI app: `/v1` routing, JSON error envelope, structured logging in `apps/api/tessera_api/main.py`
- [X] T017 [P] Wire Celery app + Redis broker (ephemeral transport; results authoritative in Postgres) in `apps/workers/tessera_workers/celery_app.py`
- [X] T018 [P] Implement Anthropic `LLMProvider` (config-driven model selection: opus-4-8 default, haiku-4-5 for drift, sonnet-4-6 option) and Voyage `EmbeddingProvider` adapters in `apps/api/tessera_api/adapters/`
- [X] T019 Implement append-only `AuditRecord` repository + write helper in `apps/api/tessera_api/adapters/audit.py`
- [X] T020 Implement minimal seam endpoints needed by all stories: create/list Space and map group→role (`POST/GET /v1/spaces`, `POST /v1/spaces/{id}/permissions`) in `apps/api/tessera_api/routers/spaces.py`
- [X] T021 [P] Implement web app shell: OIDC login, layout, shared API client in `apps/web/app/`

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 - Conhecimento estruturado e ingerido por espaço (Priority: P1) 🎯 MVP

**Goal**: Conectar um repositório Git a um espaço, ingerir artefatos e publicá-los como documentos canônicos (markdown + frontmatter), com chunking/indexação no pgvector.

**Independent Test**: Conectar um repo Git a um espaço, rodar a sincronização e verificar documentos canônicos com frontmatter completo, classificação correta, "sem dono" sinalizado, e idioma registrado.

### Tests for User Story 1 (write FIRST, must FAIL)

- [X] T022 [P] [US1] Connector contract test (output shape, idempotência, change detection, sem-dono, sem segredo em texto) in `apps/workers/tests/contract/test_connector_contract.py`
- [X] T023 [P] [US1] Integration test: git sync → DocumentVersion + frontmatter + "Sem dono" gating + idioma in `apps/workers/tests/integration/test_ingestion.py`

### Implementation for User Story 1

- [X] T024 [P] [US1] Implement Git/GitHub `Connector` plugin (diff por commit SHA, READMEs/ADRs/markdown, content_hash) in `apps/workers/tessera_workers/connectors/git.py`
- [X] T025 [US1] Implement ingestion pipeline (normalize → markdown+frontmatter → immutable DocumentVersion, persist SourceArtifact, idempotent by content_hash, language detection) in `apps/workers/tessera_workers/ingestion/`
- [X] T026 [US1] Implement chunking + embeddings + pgvector indexing of published versions (denormalized ACL metadata per chunk) in `apps/workers/tessera_workers/indexing/`
- [X] T027 [US1] Implement connector config + sync endpoints (`POST /v1/spaces/{id}/connectors`, `POST /v1/connectors/{id}/sync`) dispatching Celery jobs in `apps/api/tessera_api/routers/connectors.py`
- [X] T028 [US1] Implement document/version read + publish endpoints with "sem dono" publication gating in `apps/api/tessera_api/routers/documents.py`

**Checkpoint**: Espaços de Engenharia e RH populados via conector Git, documentos publicáveis e indexados.

---

## Phase 4: User Story 2 - Resposta citada respeitando permissões (Priority: P1) 🎯 MVP

**Goal**: Busca semântica + assistente conversacional que respondem com citações, restritos às permissões do usuário, retornando "não sei" quando a confiança é baixa.

**Independent Test**: Com espaços populados, fazer perguntas de onboarding com perfis distintos; verificar respostas corretas e citadas, restrição por permissão (sem vazamento), e "não sei" + dono sugerido quando sem cobertura.

### Tests for User Story 2 (write FIRST, must FAIL)

- [X] T029 [P] [US2] Contract test `POST /v1/assistant/answer` (sempre citação OU `dont_know`) in `apps/api/tests/contract/test_assistant.py`
- [X] T030 [P] [US2] Contract test `POST /v1/search` (ACL-first, só published) in `apps/api/tests/contract/test_search.py`
- [X] T031 [P] [US2] Integration test: usuário sem acesso a RH não vê conteúdo/existência nem como fonte (SC-007) in `apps/api/tests/integration/test_answer_permissions.py`

### Implementation for User Story 2

- [X] T032 [US2] Implement ACL-first retrieval (resolve permissões → filtro `space_id`/confidentiality/`state=published` ANTES do ANN no pgvector) in `apps/api/tessera_api/rag/retrieval.py`
- [X] T033 [US2] Implement context assembly + Citation generation (chunk id + version) in `apps/api/tessera_api/rag/citations.py`
- [X] T034 [US2] Implement assistant answer service with configurable confidence threshold + groundedness check → "não sei" + suggested owner in `apps/api/tessera_api/rag/assistant.py`
- [X] T035 [US2] Implement `/v1/search` and `/v1/assistant/answer` endpoints in `apps/api/tessera_api/routers/search.py` and `assistant.py`
- [X] T036 [P] [US2] Web search page + assistant chat with markdown rendering and clickable citations in `apps/web/app/`

**Checkpoint**: ≥80% das perguntas de onboarding respondidas com citação; permissões aplicadas; "não sei" funcional. **MVP entregável.**

---

## Phase 5: User Story 3 - Detecção de drift e atualização aprovada por humano (Priority: P2)

**Goal**: Detectar drift entre a fonte Git e a documentação publicada, gerar `UpdateProposal` com patch em markdown, e publicar nova versão apenas após aprovação do dono.

**Independent Test**: Alterar um arquivo na fonte, sincronizar, confirmar criação de proposta pendente atribuída ao dono; aprovar publica nova versão; nada é publicado sem aprovação.

### Tests for User Story 3 (write FIRST, must FAIL)

- [X] T037 [P] [US3] Integration test: source change → `UpdateProposal` pending → approve publishes new version in `apps/workers/tests/integration/test_drift.py`
- [X] T038 [P] [US3] Test: no auto-publish without explicit approval; obsolete proposal invalidated on new source change (SC-005, FR-018) in `apps/api/tests/integration/test_proposal_approval.py`

### Implementation for User Story 3

- [X] T039 [US3] Implement drift detection pipeline (content_hash change → semantic diff via embeddings + LLM classification → patch) in `apps/workers/tessera_workers/drift/`
- [X] T040 [US3] Implement proposal lifecycle in domain (pending/approved/rejected/invalidated, obsolete invalidation, owner-less escalation to space admin) in `packages/core/tessera_core/services/proposals.py`
- [X] T041 [US3] Implement proposal review endpoints (`GET /v1/proposals`, `GET /v1/proposals/{id}`, `POST .../approve` → new version, `POST .../reject` + reason) in `apps/api/tessera_api/routers/proposals.py`
- [X] T042 [US3] Mark document `Desatualizado` on drift while continuing to serve the prior published version in `apps/api/tessera_api/` + `packages/core`
- [X] T043 [P] [US3] Web proposal review queue UI (diff view, approve/reject with reason) in `apps/web/app/proposals/`

**Checkpoint**: Drift detectado a partir do Git gera propostas; human-in-the-loop garantido.

---

## Phase 6: User Story 4 - Agente de IA consome via MCP/API respeitando permissões (Priority: P2)

**Goal**: Servidor MCP e API para agentes, com tokens de serviço escopados por espaço e enforcement de permissões no servidor; `restricted` fora do índice de agentes.

**Independent Test**: Credencial escopada só em Engenharia; consultar Engenharia retorna conteúdo+citações; consultar RH confidencial retorna 0 resultados sem vazamento; cada chamada auditada.

### Tests for User Story 4 (write FIRST, must FAIL)

- [X] T044 [P] [US4] MCP contract test (`search_documents`/`read_document` structure: markdown + metadados + citação) in `apps/mcp-server/tests/contract/test_mcp_tools.py`
- [X] T045 [P] [US4] MCP permission test: scoped agent, 0 leaks for out-of-scope/restricted (SC-003/SC-007) in `apps/mcp-server/tests/test_mcp_permissions.py`
- [X] T046 [P] [US4] Parity test: MCP `search_documents` == REST `/v1/search` for identical permissions in `apps/mcp-server/tests/test_parity.py`

### Implementation for User Story 4

- [X] T047 [US4] Implement AgentCredential issuance/revocation + bearer token auth in `apps/api/tessera_api/routers/agent_credentials.py` and `apps/api/tessera_api/auth/`
- [X] T048 [US4] Implement MCP server with `search_documents`/`read_document` tools, server-side enforcement reusing `core.permissions`, `restricted` excluded in `apps/mcp-server/tessera_mcp/`
- [X] T049 [US4] Audit every agent query/read (who consulted what) via the shared audit helper in `apps/mcp-server/tessera_mcp/`
- [X] T050 [US4] Enable bearer (service-token) auth for `/v1` agent-facing endpoints in `apps/api/tessera_api/auth/`

**Checkpoint**: Servidor MCP consumido por agente externo com permissões respeitadas (0 vazamentos).

---

## Phase 7: User Story 5 - Administração de espaços, conectores e permissões (Priority: P3)

**Goal**: Painel administrativo completo: espaços, mapeamento de permissões via SSO, conectores, retenção, e credenciais de agente.

**Independent Test**: Criar espaço, mapear grupo de SSO a papel, e confirmar que membros recebem exatamente o acesso configurado e a mudança é auditada; retenção expira documentos.

### Tests for User Story 5 (write FIRST, must FAIL)

- [X] T051 [P] [US5] Integration test: group→role mapping grants exact access and is audited; retention expires document and removes it from index in `apps/api/tests/integration/test_admin.py`

### Implementation for User Story 5

- [X] T052 [US5] Implement admin endpoints: full Space management, permission mapping, retention policy config, connector config in `apps/api/tessera_api/routers/admin.py`
- [X] T053 [US5] Implement retention/validity job (expire documents → Expirado/Arquivado → remove from response index) in `apps/workers/tessera_workers/retention/`
- [X] T054 [P] [US5] Admin web UI (spaces, connectors, permissions, agent credentials, retention) in `apps/web/app/admin/`

**Checkpoint**: Administração completa configurável; todas as user stories funcionais.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Métricas, conformidade, observabilidade, segurança e validação final

- [X] T055 [P] Implement LLM-as-judge evaluation harness vs versioned reference answer set per space (FR-027) in `apps/api/tessera_api/eval/`
- [X] T056 [P] Implement metrics endpoint + internal dashboard (correct/dont_know/drift/time-to-approval) `GET /v1/metrics` and `apps/web/app/metrics/` (FR-026, SC-008)
- [X] T057 Build adversarial cross-sector/role/agent permission test suite for both human and MCP paths (SC-007) in `apps/api/tests/security/` and `apps/mcp-server/tests/security/`
- [X] T058 [P] Implement LGPD compliance: data minimization, subject rights (access/erasure), version redaction (FR-025a) in `apps/api/tessera_api/` + `packages/core`
- [X] T059 [P] Add OpenTelemetry traces/metrics + structured logs across api/workers/mcp
- [X] T060 Performance validation against SC-009 (search <2s p95, assistant start <5s p95) under representative MVP load
- [X] T061 [P] Author Kubernetes manifests for the chosen production provider in `deploy/k8s/`
- [X] T062 Run quickstart.md V1–V8 end-to-end validation and confirm success criteria

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational.
  - US1 (P1) and US2 (P1) are the MVP; US2 depends on US1 having indexed content (or seeded published docs) to answer.
  - US3 (P2) depends on US1 (needs published docs + connectors to detect drift).
  - US4 (P2) depends on US1/US2 (reuses retrieval + permissions; needs indexed content).
  - US5 (P3) extends the foundational seam (T020) into a full admin surface; independently testable.
- **Polish (Phase 8)**: Depends on the desired user stories being complete.

### User Story Dependencies

- US1 → none beyond Foundational.
- US2 → Foundational + content from US1 (or manually seeded published documents) to be meaningfully testable.
- US3 → US1 (published docs + connector source).
- US4 → US1 (indexed content) + reuses US2 retrieval/permissions.
- US5 → Foundational only (admin surface); does not block other stories.

### Within Each User Story

- Tests written FIRST and FAIL before implementation (TDD).
- Domain/models → services → endpoints → UI.
- `core.permissions` and drift modules carry the highest coverage priority.

### Parallel Opportunities

- Setup: T002–T006 in parallel.
- Foundational: T009, T010, T011, T015, T016, T017, T018, T021 in parallel (distinct files); T012 after T011; T014 after T009.
- Once Foundational completes, US1–US5 can be staffed in parallel (mind the content dependencies above).
- Within a story, all `[P]` tests and `[P]` implementation files run in parallel.

---

## Parallel Example: User Story 1

```bash
# Tests first (must fail):
Task: "Connector contract test in apps/workers/tests/contract/test_connector_contract.py"
Task: "Integration test for ingestion in apps/workers/tests/integration/test_ingestion.py"

# Then parallelizable implementation:
Task: "Git/GitHub Connector plugin in apps/workers/tessera_workers/connectors/git.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (US1 — ingestion) → validate independently.
3. Complete Phase 4 (US2 — cited answers with permissions) → validate.
4. **STOP and VALIDATE**: this is the MVP delivering SC-001/SC-004/SC-007/SC-009.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → US2 → MVP demo.
3. US3 (drift + approval) → demo (SC-002/SC-005).
4. US4 (MCP/agents) → demo (SC-003).
5. US5 (admin) → demo.
6. Polish (metrics, LGPD, observability, adversarial security, perf, k8s) → SC-006/SC-007/SC-008.

### Parallel Team Strategy

After Foundational: Dev A on US1, Dev B on US2 (coordinating retrieval), Dev C on US5 (admin), then US3/US4 once US1 content exists.

---

## Notes

- `[P]` = different files, no incomplete-task dependencies.
- `[Story]` labels map tasks to spec.md user stories for traceability.
- Verify tests fail before implementing (constitutional TDD).
- Quality gates (Ruff/Black) and ≥85% coverage block commits.
- Honor the 3 documented constitution deviations (no Cassandra, Redis-as-broker, K8s deferred) from plan.md Complexity Tracking.
- Total: 62 tasks (T001–T062).
