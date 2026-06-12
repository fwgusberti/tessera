# Contract: REST API (gateway humano + agentes)

Aplicação `api` (FastAPI). Autenticação humana via sessão OIDC; agentes via `Authorization: Bearer <service-token>`. Todas as respostas respeitam permissões do solicitante (RBAC por espaço + confidencialidade). Erros usam JSON `{ "error": { "code", "message" } }`. Formatos abaixo são o contrato lógico (request/response shape), não a implementação.

## Convenções
- Versão: prefixo `/v1`.
- AuthZ: cada endpoint resolve o conjunto de espaços/níveis permitidos antes de consultar dados. Conteúdo `restricted` nunca aparece para quem não tem permissão (nem sua existência — 404, não 403, para não vazar metadados).
- Auditoria: toda mutação e toda leitura de assistente/agente emite `AuditRecord`.

## Espaços e documentos

### `POST /v1/spaces` (admin)
Cria espaço. Body: `{ slug, name, sector, default_language, retention_policy?, confidence_threshold? }` → `201 { space }`.

### `GET /v1/spaces` → `200 { spaces: [...] }`
Apenas espaços visíveis ao solicitante.

### `POST /v1/spaces/{id}/permissions` (admin)
Mapeia grupo do IdP a papel. Body: `{ idp_group, role, max_confidentiality }` → `201 { permission }`.

### `GET /v1/documents?space_id=&state=` → `200 { documents: [...] }`
Lista documentos visíveis; filtra por estado/espaço.

### `POST /v1/documents` (contributor+)
Cria documento (autoria direta). Body: `{ space_id, title, language, confidentiality, tags?, content_markdown, frontmatter }` → `201 { document, version }`. Estado inicial `Ingerido`/`Sem dono` até atribuição+publicação.

### `GET /v1/documents/{id}` → `200 { document, current_version }`
404 se não permitido.

### `GET /v1/documents/{id}/versions` → `200 { versions: [...] }`
Histórico imutável (FR-023).

### `POST /v1/documents/{id}/publish` (owner/admin)
Publica versão corrente; registra aprovador (FR-024). → `200 { document, version }`.

## Busca e assistente

### `POST /v1/search`
Busca semântica ACL-first. Body: `{ query, space_ids?, language?, top_k? }` →
`200 { results: [{ document_id, version_id, chunk_id, score, snippet, citation }] }`.
Apenas documentos `published` e permitidos.

### `POST /v1/assistant/answer`
Resposta conversacional com citações. Body: `{ query, space_ids?, language? }` →
`200 { answer, citations: [{ chunk_id, document_version_id, quote, score }], confidence }`
ou `200 { answer: null, dont_know: true, suggested_owner: { space_id, owner } }` quando confiança < limiar (FR-011, SC-004).
**Garantia**: toda afirmação factual tem ≥1 citação; nenhum conteúdo fora da permissão é citado ou revelado (FR-010/FR-012).

## Propostas de atualização (drift)

### `GET /v1/proposals?state=pending&space_id=` → `200 { proposals: [...] }`
Fila de revisão; para o dono, propostas dos seus documentos; admin vê escaladas (FR-017).

### `GET /v1/proposals/{id}` → `200 { proposal, diff, target_document }`

### `POST /v1/proposals/{id}/approve` (owner/admin)
Publica nova `DocumentVersion` a partir do patch; registra aprovador (FR-015/FR-016). → `200 { document, version }`.

### `POST /v1/proposals/{id}/reject` (owner/admin)
Body: `{ reason? }` → `200 { proposal }`. Documento permanece inalterado (FR-015).

## Administração de conectores

### `POST /v1/spaces/{id}/connectors` (admin)
Body: `{ type: "git", config: { repo_url, branch, credential_ref }, schedule? }` → `201 { connector }`.

### `POST /v1/connectors/{id}/sync` (admin)
Dispara ingestão sob demanda → `202 { job_id }`.

## Credenciais de agente

### `POST /v1/agent-credentials` (admin)
Body: `{ name, scoped_space_ids, max_confidentiality }` → `201 { credential, token }` (token exibido uma única vez).

### `POST /v1/agent-credentials/{id}/revoke` (admin) → `200 { credential }`.

## Métricas

### `GET /v1/metrics` (admin)
→ `200 { correct_answer_rate, dont_know_rate, documents_with_drift, time_to_approval_p50, time_to_approval_p90 }` (FR-026, SC-008).

## Testes de contrato (obrigatórios)
- AuthZ matrix: para cada endpoint, usuário sem permissão recebe 404 (não vaza existência) em recurso `restricted`/fora de escopo (SC-007).
- `assistant/answer`: resposta sempre com citação OU `dont_know=true` (SC-004).
- `proposals/approve`: só publica após chamada explícita; nunca por efeito colateral de ingestão (SC-005).
