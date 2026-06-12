# Quickstart & Validation Guide: Tessera

Guia para subir o ambiente de desenvolvimento e validar o MVP de ponta a ponta contra os critérios de sucesso da spec. Não contém implementação — apenas pré-requisitos, comandos e resultados esperados. Detalhes de modelo/entidades estão em [data-model.md](./data-model.md) e os formatos em [contracts/](./contracts/).

## Pré-requisitos
- Docker + Docker Compose
- Python 3.12 (com `uv` ou `pip`) e Node 22+ (apenas para desenvolvimento fora dos contêineres)
- Variáveis de ambiente (injetadas, nunca commitadas):
  - `ANTHROPIC_API_KEY` (LLM), `VOYAGE_API_KEY` (embeddings)
  - `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_ISSUER` (Google Workspace no MVP)
  - `DATABASE_URL` (PostgreSQL 16 + pgvector), `REDIS_URL`
  - `GITHUB_TOKEN_REF` (referência ao segredo do conector Git de teste)

## Subir o ambiente (dev)
```bash
docker compose -f deploy/docker-compose.yml up -d   # postgres+pgvector, redis, api, worker, mcp, web
# aplicar migrações (cria schema + extensão pgvector)
docker compose exec api alembic upgrade head
```
Serviços esperados: `api` (FastAPI), `worker` (Celery), `mcp` (servidor MCP), `web` (Next.js), `postgres`, `redis`.

## Qualidade e testes (gates da constituição)
```bash
ruff check . && black --check .            # quality gates — bloqueiam commit
pytest --cov=packages/core --cov=apps --cov-report=term-missing --cov-fail-under=85
```
Esperado: lint/format limpos; cobertura global ≥85%, com módulos `core/permissions` e `workers/drift` no nível mais alto de cobertura (TDD prioritário).

---

## Cenários de validação (mapeados aos critérios de sucesso)

### V1 — Ingestão popula espaços (US1, SC-001 parcial)
1. Como admin, crie os espaços `engineering` e `hr` (`POST /v1/spaces`).
2. Conecte um repositório Git de teste a cada espaço (`POST /v1/spaces/{id}/connectors`) e dispare `POST /v1/connectors/{id}/sync`.
3. **Esperado**: documentos aparecem com markdown canônico + frontmatter completo; artefatos sem dono ficam em `Sem dono` e listados para atribuição; idioma registrado por documento.

### V2 — Resposta citada respeitando permissões (US2, SC-004/SC-007)
1. Atribua donos e publique os documentos de onboarding (`POST /v1/documents/{id}/publish`).
2. Como usuário com acesso a RH, `POST /v1/assistant/answer { "query": "como solicito férias?" }`.
   - **Esperado**: resposta correta com ≥1 citação rastreável.
3. Como usuário **sem** acesso a RH, pergunte sobre uma política `restricted`.
   - **Esperado**: o conteúdo/existência não é revelado; não é usado como fonte.
4. Pergunte algo sem cobertura.
   - **Esperado**: `dont_know: true` + dono/espaço sugerido (SC-004).

### V3 — Busca semântica sob meta de performance (SC-009)
1. `POST /v1/search { "query": "deploy em produção", "space_ids": ["<eng>"] }`.
2. **Esperado**: resultados apenas `published` e permitidos; latência <2s (p95) sob carga representativa; resposta do assistente começa <5s (p95).

### V4 — Drift com aprovação humana (US3, SC-002/SC-005)
1. Altere um README/markdown na fonte conectada; rode `POST /v1/connectors/{id}/sync`.
2. **Esperado**: o pipeline cria uma `UpdateProposal` (estado `pending`) atribuída ao dono, com patch em markdown e resumo do drift; documento marcado `Desatualizado`, mas a versão publicada anterior continua servida.
3. Aprove via `POST /v1/proposals/{id}/approve`.
   - **Esperado**: nova `DocumentVersion` publicada com aprovador e timestamp; auditoria registra a aprovação.
4. (Negativo) Confirme que **nenhuma** nova versão foi publicada antes da aprovação (SC-005).

### V5 — Agente via MCP respeitando permissões (US4, SC-003/SC-007)
1. Crie `AgentCredential` com escopo só em `engineering` (`POST /v1/agent-credentials`).
2. Conecte um agente externo ao `mcp-server` usando o token; chame `search_documents` para um tópico de Engenharia.
   - **Esperado**: conteúdo markdown + metadados + citações.
3. Com a mesma credencial, chame `search_documents`/`read_document` para um tópico de RH confidencial.
   - **Esperado**: 0 resultados / erro `not_found`; nenhum vazamento (0 vazamentos em testes de permissão — SC-003).
4. **Esperado**: cada chamada gera um `AuditRecord` (qual agente consultou o quê).

### V6 — Administração, versionamento e auditoria (US5, SC-006)
1. Como admin, mapeie um grupo do IdP a um papel em um espaço (`POST /v1/spaces/{id}/permissions`).
   - **Esperado**: membros do grupo passam a ter exatamente o acesso configurado; mudança registrada em auditoria.
2. Consulte `GET /v1/documents/{id}/versions`.
   - **Esperado**: histórico imutável consultável; toda mudança de estado tem `AuditRecord` com ator/timestamp/entidade (SC-006).

### V7 — Métricas de qualidade (SC-008)
1. Rode o conjunto de avaliação versionado de onboarding (LLM-as-judge) por espaço.
2. `GET /v1/metrics` (admin).
   - **Esperado**: `correct_answer_rate` ≥ 80% para onboarding; `dont_know_rate`, `documents_with_drift`, `time_to_approval_*` disponíveis no dashboard.

### V8 — Testes de permissão adversariais (SC-007)
- Execute a suíte adversarial cruzando setores/papéis/credenciais de agente.
- **Esperado**: 0 vazamentos — documentos confidenciais (ex.: RH) nunca expostos (conteúdo, citação ou existência) a quem não tem acesso, em ambos os caminhos (humano e MCP).

---

## Critério de "pronto para tasks"
Todos os V1–V8 descritos e rastreáveis aos critérios de sucesso da spec; contratos (REST, MCP, Connector) com testes de contrato definidos; gates de qualidade e cobertura configurados. A decomposição em tarefas é gerada por `/speckit-tasks`.
