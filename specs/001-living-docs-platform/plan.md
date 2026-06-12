# Implementation Plan: Plataforma de Documentação Viva (Tessera)

**Branch**: `001-living-docs-platform` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-living-docs-platform/spec.md`

## Summary

Tessera é uma camada de conhecimento viva, consumida por humanos e por agentes de IA. O MVP ingere artefatos de repositórios Git para espaços setoriais (Engenharia, RH), publica documentos canônicos em markdown + frontmatter com versionamento e auditoria, serve respostas com citações via busca semântica e assistente conversacional (RAG com permissões aplicadas antes da busca vetorial), expõe o conhecimento a agentes via API e servidor MCP escopado por permissões, e mantém a documentação atualizada detectando drift entre a fonte da verdade e a documentação publicada — gerando propostas de atualização aprovadas por humanos (human-in-the-loop obrigatório).

Abordagem técnica: monorepo com três aplicações (`api` FastAPI, `web` Next.js, `mcp-server`) e um pacote compartilhado `core` com modelos de domínio e lógica de permissões livre de framework. PostgreSQL 16 como fonte única de verdade, incluindo busca vetorial via pgvector (sem vector DB separado no MVP). Celery + Redis para pipelines assíncronos de ingestão, indexação e drift. Provider de LLM (Anthropic Claude) e de embeddings (Voyage AI) abstraídos atrás de interfaces para troca futura.

## Technical Context

**Language/Version**: Python 3.12 (backend, `core`, `api`, `mcp-server`); TypeScript 5.x / Node 22+ (frontend `web`)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.x + Alembic, Pydantic v2, Celery, `anthropic` SDK (LLM), Voyage AI client (embeddings), MCP Python SDK (servidor MCP), Authlib/OIDC para SSO
- Banco/busca: PostgreSQL 16 + extensão `pgvector`
- Frontend: Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui, renderização de markdown com citações clicáveis
- Observabilidade: OpenTelemetry (traces/metrics) + logging estruturado

**Storage**: PostgreSQL 16 (relacional + vetorial via pgvector) como fonte única de verdade. Redis usado **apenas** como broker/transport efêmero do Celery (ver Constitution Check). Documentos canônicos persistidos como markdown + frontmatter em colunas de texto/JSONB.

**Testing**: pytest (+ pytest-cov) no backend; cobertura mínima global ≥85% (constituição), com TDD prioritário e mais rigoroso nos módulos de **permissões** e **drift**; testes de contrato para conectores e para o protocolo MCP. Frontend: Vitest + Testing Library (componentes críticos de citação/markdown).

**Target Platform**: Servidores Linux em contêineres. Dev via Docker Compose; produção em provedor cloud único com PostgreSQL gerenciado (decisão de provedor adiada — sem acoplamento a serviços proprietários além do banco).

**Project Type**: Web (monorepo com backend + frontend + servidor MCP + pacote compartilhado).

**Performance Goals** (de SC-009): busca semântica <2s (p95); início da resposta do assistente <5s (p95), sob carga representativa do MVP.

**Constraints**:
- Filtro de ACL aplicado **antes** da busca vetorial (filtro no pgvector); nunca pós-filtrar contexto já enviado ao LLM.
- Nenhum dado de documento `restricted` enviado a LLM externo sem verificação de confidencialidade; documentos `restricted` ficam fora do índice de agentes.
- Toda resposta retorna citações com IDs de chunk; score de recuperação baixo ⇒ responder "não sei" e indicar o dono do espaço.
- Enforcement de permissões do MCP **no servidor**, nunca no cliente; agentes autenticam com tokens de serviço escopados por espaço.
- Documentos sempre em markdown + frontmatter YAML; nunca HTML proprietário.
- Conformidade LGPD para dados pessoais/sensíveis (RH): minimização, finalidade, direitos do titular, retenção limitada.

**Scale/Scope** (de Assumptions/SC-009): até ~10k documentos, ~500 usuários, ~10 espaços no MVP.

**Model selection** (Anthropic, abstraído atrás de `LLMProvider`; preços por 1M tokens):
- Geração de respostas do assistente e geração de propostas de atualização: **`claude-opus-4-8`** (padrão; $5 in / $25 out), com thinking adaptativo e prompt caching do system prompt/contexto estável.
- Classificação de drift (tarefa de baixo custo/alto volume): configurável para **`claude-haiku-4-5`** ($1 in / $5 out) quando o custo importar; padrão seguro `claude-opus-4-8`.
- Alternativa de alto volume sensível a custo para respostas: **`claude-sonnet-4-6`** ($3 in / $15 out), selecionável por configuração.
- Embeddings: **Voyage AI** (família `voyage-3`) atrás de `EmbeddingProvider`; dimensão registrada na coluna `vector` do pgvector.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Avaliação contra `.specify/memory/constitution.md` v1.0.0:

| Princípio | Status | Como o plano atende |
|-----------|--------|---------------------|
| I. Domain-Driven Architecture | ✅ | Pacote `core` contém modelos de domínio + lógica de permissões, sem importar FastAPI/SQLAlchemy/Celery. Adaptadores de infraestrutura ficam em `api`/`mcp-server`/`workers`. |
| II. Separation of Concerns | ✅ | Domínio agnóstico de banco/transporte; provider de LLM/embeddings atrás de interfaces (`LLMProvider`, `EmbeddingProvider`); conectores como plugins (`Connector`). |
| III. Data Locality & Consent | ✅ | Sem persistência de dados de usuário no cliente sem consentimento. Frontend não armazena conteúdo de documentos localmente; sessão via cookie seguro. LGPD reforça consentimento/finalidade. |
| IV. Test-Driven Development | ✅ | TDD com falha-primeiro; cobertura global ≥85%; permissões e drift como alvos prioritários e com testes adversariais (SC-007). |
| V. Quality Gates | ✅ | Ruff + Black bloqueiam commit (pre-commit + CI). |
| Stack: PostgreSQL como sistema de registro | ✅ | PostgreSQL 16 é o sistema de registro único (relacional + não-relacional via JSONB/pgvector), conforme constituição v1.2.0. |
| Stack: Caching & message transport | ✅ | Redis como broker efêmero do Celery é permitido pela constituição v1.1.0+ (cache/broker nunca é sistema de registro). |
| Stack: IaC com Docker + Kubernetes | ⚠️ Desvio | Docker Compose no dev; K8s adiado para hardening de produção — ver Complexity Tracking. |
| Security: OAuth2 + JWT no gateway | ✅ | SSO via OIDC (OAuth2); sessões/JWT no gateway; MCP com tokens de serviço escopados. |
| Security: gestão de segredos via env | ✅ | Segredos por injeção de ambiente; nada commitado. |
| Security: audit logging de mudanças de estado | ✅ | Tabela append-only de auditoria (ator, timestamp, entidade) — FR-024. |
| Documentation separation (spec vs plan) | ✅ | spec.md sem tecnologia; plan.md concentra o HOW. |

**Gate**: PASS com 1 desvio justificado (Kubernetes). Os desvios de armazenamento (Cassandra) e de broker (Redis) foram resolvidos pelas emendas da constituição v1.1.0 (caching & message transport) e v1.2.0 (PostgreSQL como sistema de registro único) e não são mais desvios. Nenhum desvio compromete princípios inegociáveis (DDD, TDD, quality gates, segurança). Registrado em Complexity Tracking; reavaliar o item de Kubernetes no hardening de produção.

## Project Structure

### Documentation (this feature)

```text
specs/001-living-docs-platform/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (REST + MCP + Connector)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
packages/
└── core/                       # Domínio puro (sem framework) — Python 3.12
    ├── tessera_core/
    │   ├── domain/             # Space, Document, Version, Chunk, UpdateProposal, etc.
    │   ├── permissions/        # RBAC por espaço + confidencialidade; decisão de acesso pura
    │   ├── ports/              # Interfaces: LLMProvider, EmbeddingProvider, Connector, repositórios
    │   └── services/           # Regras de domínio: ciclo de vida do documento, drift, citações
    └── tests/                  # Unit/TDD do domínio (permissões e drift priorizados)

apps/
├── api/                        # FastAPI (gateway humano + REST para agentes)
│   ├── tessera_api/
│   │   ├── routers/            # spaces, documents, search, assistant, proposals, admin, metrics
│   │   ├── auth/               # OIDC (Google Workspace), sessão, RBAC enforcement
│   │   ├── adapters/           # SQLAlchemy repos, pgvector, Anthropic, Voyage, OTel
│   │   ├── rag/                # recuperação ACL-first, montagem de contexto, citações
│   │   └── main.py
│   └── tests/                  # contract + integration
├── mcp-server/                 # Servidor MCP (SDK oficial Python) para agentes
│   ├── tessera_mcp/
│   │   ├── tools/              # search_documents, read_document (enforcement no servidor)
│   │   ├── auth/               # tokens de serviço escopados por espaço
│   │   └── server.py
│   └── tests/                  # contract (protocolo MCP) + permission tests
├── workers/                    # Celery: ingestão, chunking/indexação, detecção de drift
│   ├── tessera_workers/
│   │   ├── connectors/         # implementações do port Connector (git/github no MVP)
│   │   ├── ingestion/          # normalização → markdown+frontmatter → versão
│   │   ├── indexing/           # chunking + embeddings + escrita no pgvector
│   │   └── drift/              # diff semântico + geração de UpdateProposal
│   └── tests/                  # contract de conectores + drift
└── web/                        # Next.js 15 (App Router), TS, Tailwind, shadcn/ui
    ├── app/                    # busca, assistente (citações clicáveis), revisão de propostas, admin
    ├── components/
    └── tests/                  # Vitest + Testing Library

db/
└── migrations/                 # Alembic (schema + extensão pgvector)

deploy/
├── docker-compose.yml          # dev: postgres+pgvector, redis, api, worker, web, mcp
└── Dockerfile.*                # imagens por aplicação
```

**Structure Decision**: Monorepo web com quatro unidades de execução Python (`api`, `mcp-server`, `workers` + pacote `core`) e a aplicação `web` em TypeScript. O pacote `core` concentra domínio e permissões livres de framework (Princípios I/II); `workers` hospeda Celery e os conectores-plugin; `api` e `mcp-server` são os dois adaptadores de entrega que reusam `core`. Esta separação garante que a lógica de permissões (a mais crítica para SC-003/SC-007) seja testável isoladamente e reusada de forma idêntica por humanos (api) e agentes (mcp-server).

## Complexity Tracking

> Desvios da constituição que exigem justificativa.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Docker Compose no dev, sem manifests Kubernetes (constituição: IaC com Docker + K8s) | A decisão de provedor de produção foi explicitamente adiada; comprometer-se com K8s agora acoplaria a infraestrutura prematuramente. Tudo já é declarado como código (Compose + Dockerfiles). | Escrever manifests K8s antes de definir o provedor produziria IaC especulativo e provavelmente refeito. Plano: adicionar manifests K8s na fase de "Métricas e hardening" (T061), quando o provedor for escolhido. |

> Nota: os antigos desvios de **Cassandra** e **Redis** foram resolvidos por emendas da constituição (v1.1.0 caching & message transport; v1.2.0 PostgreSQL como sistema de registro único) e removidos desta tabela.

## Implementation Phases (do enunciado, refinadas)

1. **Fundação**: pacote `core` (domínio + permissões + ports), schema/migrations (Space→Document→Version→Chunk + auditoria), auth OIDC/RBAC, CRUD de espaços/documentos com versionamento imutável e ciclo de vida (FR-001..FR-004, FR-023/FR-024). TDD prioritário em permissões.
2. **Ingestão**: port `Connector` + conector Git/GitHub (MVP), pipeline Celery de normalização → markdown+frontmatter → versão; chunking + embeddings (Voyage) + indexação no pgvector com metadados de ACL por chunk (FR-005..FR-007). Testes de contrato de conector.
3. **Consumo**: recuperação ACL-first no pgvector, montagem de contexto e citações, assistente (Claude) com "não sei" por baixo score, busca semântica, e servidor MCP com tools `search_documents`/`read_document` e enforcement no servidor (FR-008..FR-012, FR-019/FR-020, SC-001/SC-003/SC-004/SC-009).
4. **Drift**: evento de mudança de fonte → diff semântico (embeddings + LLM) → `UpdateProposal` com patch em markdown → fila de revisão do dono → publicação só após aprovação; invalidação de propostas obsoletas (FR-013..FR-018, SC-002/SC-005).
5. **Métricas e hardening**: auditoria completa, dashboard de métricas de produto (corretas/“não sei”/drift/tempo até aprovação), avaliação automatizada LLM-as-judge (FR-026/FR-027, SC-008), testes de permissão adversariais (SC-007), conformidade LGPD (FR-025a), e manifests Kubernetes para o provedor de produção escolhido.

## Artifacts

- Phase 0: [research.md](./research.md)
- Phase 1: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)
