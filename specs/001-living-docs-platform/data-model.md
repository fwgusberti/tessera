# Phase 1 Data Model: Tessera

Modelo de domínio derivado de spec.md (Key Entities) e do enunciado técnico (Space → Document → Version → Chunk). Tipos descritos de forma agnóstica; a implementação usa PostgreSQL 16 + pgvector e SQLAlchemy. Todos os IDs são UUID. Campos `created_at`/`updated_at` implícitos onde aplicável.

## Diagrama de relacionamentos (texto)

```
Space 1──* Document 1──* DocumentVersion
  │            │  *──1 User (owner)         (DocumentVersion *──1 User author, *──0..1 User approver)
  │            └──* Chunk *──1 DocumentVersion   (Chunk carrega embedding + metadados de ACL)
  │
Space 1──* Connector 1──* SourceArtifact 1──* (origem de) DocumentVersion
Space 1──* RolePermission *──1 (Group do IdP)        Document 1──* UpdateProposal *──1 SourceArtifact
User *──* Group (via IdP)                            AgentCredential *──* Space (escopo)
AuditRecord *──1 (actor: User | AgentCredential)     Citation *──1 Chunk, *──1 (Answer/Proposal)
```

## Entidades

### Space (Espaço)
Agrupamento setorial de conhecimento.
- `id`, `slug`, `name`, `sector` (ex.: engineering, hr)
- `taxonomy` (JSONB: tags/estrutura permitidas)
- `retention_policy` (JSONB: validade padrão, ação na expiração)
- `confidence_threshold` (float configurável para "não sei")
- `default_language` (pt-BR | en)
- **Regras**: nome/slug únicos; espaço deve ter ≥1 papel com nível administrativo.

### Document (Documento)
Unidade canônica de conhecimento.
- `id`, `space_id` (FK), `owner_user_id` (FK, nullable enquanto "sem dono")
- `title`, `language` (pt-BR | en)
- `confidentiality` (enum: `public_internal` | `internal` | `confidential` | `restricted`)
- `tags` (string[]), `validity_until` (date, nullable)
- `state` (enum de ciclo de vida — ver máquina de estados)
- `current_version_id` (FK → DocumentVersion, nullable até primeira publicação)
- **Regras**: pertence a exatamente um Space (FR-003); `state=published` exige `owner_user_id` e `current_version_id` (FR-003); apenas `state=published` é indexável para resposta (FR-003a); `restricted` nunca exposto a agentes.

### DocumentVersion (Versão de Documento)
Estado imutável de um documento em um ponto no tempo.
- `id`, `document_id` (FK), `version_number` (monotônico por documento)
- `content_markdown` (texto: markdown), `frontmatter` (JSONB: dono, setor, validade, tags, confidencialidade, idioma)
- `author_user_id` (FK), `approver_user_id` (FK, nullable), `approved_at` (nullable)
- `source_artifact_id` (FK, nullable — origem quando derivada de conector)
- `created_from_proposal_id` (FK → UpdateProposal, nullable)
- **Regras**: imutável após criação (FR-023); publicação registra aprovador + timestamp (FR-024); frontmatter sempre presente e completo (FR-002).

### Chunk (Unidade indexada)
Fragmento de uma versão de documento, indexado para busca vetorial.
- `id`, `document_version_id` (FK), `document_id` (FK desnormalizado), `space_id` (FK desnormalizado)
- `ordinal`, `text`, `embedding` (vector — dimensão do modelo Voyage)
- `confidentiality` (desnormalizado do documento para filtro ACL-first), `language`
- **Regras**: gerado apenas para a versão publicada corrente; metadados de ACL (`space_id`, `confidentiality`) desnormalizados para permitir filtro **antes** do ANN (constraint do plano); reindexado ao publicar nova versão; removido quando o documento sai de `published`.

### Source/Connector (Fonte/Conector)
Configuração de ingestão a partir de um sistema externo.
- `id`, `space_id` (FK), `type` (`git` no MVP), `config` (JSONB: repo URL, branch, credencial ref)
- `schedule` (cron), `last_sync_at`, `status` (ok | failing)
- **Regras**: vinculado a um Space (FR-006); credenciais por referência a segredo injetado, nunca em texto.

### SourceArtifact (Artefato de Origem)
Item bruto ingerido de uma fonte.
- `id`, `connector_id` (FK), `external_id`, `path`, `source_version` (ex.: commit SHA)
- `raw_content`, `content_hash`, `fetched_at`
- **Regras**: rastreabilidade origem→versão (FR-007); `content_hash` usado para detectar mudança/drift.

### UpdateProposal (Proposta de Atualização)
Edição sugerida derivada de drift.
- `id`, `document_id` (FK), `source_artifact_id` (FK), `proposed_markdown_patch` (texto)
- `state` (enum: `pending` | `approved` | `rejected` | `invalidated`)
- `created_at`, `decided_by_user_id` (nullable), `decided_at` (nullable), `rejection_reason` (nullable)
- `drift_score`, `summary` (explicação da divergência)
- **Regras**: criada ao detectar drift (FR-014); aprovação publica nova `DocumentVersion` (FR-015); rejeição registra motivo opcional (FR-015); proposta de documento sem dono escala ao admin do espaço (FR-017); mudança nova da fonte invalida proposta pendente (FR-018); nunca publica sem decisão humana (FR-016).

### User (Usuário)
Identidade autenticada via SSO.
- `id`, `external_subject` (sub do OIDC), `email`, `display_name`, `is_admin`
- `groups` (string[] do IdP), `default_language`
- **Regras**: autenticado via OIDC (FR-021); permissões derivadas de grupos→papéis.

### Group / RolePermission (Papel/Permissão)
Mapeamento de grupos do IdP a níveis de acesso por espaço.
- `id`, `space_id` (FK), `idp_group` (string), `role` (enum: `reader` | `contributor` | `owner` | `space_admin`)
- `max_confidentiality` (nível máximo de confidencialidade legível por este papel)
- **Regras**: aplica acesso granular por setor/papel/documento (FR-022); decisão de acesso é função pura em `core.permissions`.

### AgentCredential (Credencial de Agente)
Identidade não-humana para consumo via API/MCP.
- `id`, `name`, `token_hash`, `scoped_space_ids` (UUID[]), `max_confidentiality`
- `created_by_user_id`, `revoked_at` (nullable)
- **Regras**: escopo por espaço (enunciado); enforcement no servidor MCP; `restricted` nunca acessível a agentes (constraint do plano); leituras registradas em auditoria.

### AuditRecord (Registro de Auditoria)
Evento append-only de mudança de estado ou acesso.
- `id`, `actor_type` (`user` | `agent`), `actor_id`, `action` (enum: publish, approve, reject, permission_change, ingest, read, query)
- `entity_type`, `entity_id`, `occurred_at`, `metadata` (JSONB)
- **Regras**: append-only (sem update/delete); cobre toda mudança de estado e quem leu/consultou o quê (FR-024, SC-006).

### Citation (Citação)
Referência rastreável de uma resposta/proposta a uma fonte.
- `id`, `answer_id`/`proposal_id` (origem), `chunk_id` (FK), `document_version_id` (FK)
- `quote` (trecho citado), `score`
- **Regras**: toda afirmação do assistente tem ≥1 citação (FR-010, SC-004); citação nunca expõe conteúdo fora da permissão do solicitante (FR-012).

## Máquina de estados do Documento (FR-003a)

```
Ingerido ──(atribuir dono)──▶ (com dono) ──(publicar c/ aprovação)──▶ Publicado
   │                                                                      │
   └──(sem dono identificado)──▶ Sem dono ──(atribuir + publicar)─────────┘
                                                                          │
Publicado ──(drift detectado)──▶ Desatualizado ──(proposta aprovada → nova versão)──▶ Publicado
Publicado ──(validade atingida / retenção)──▶ Expirado/Arquivado
```

- Apenas **Publicado** é indexável para resposta/citação.
- `Sem dono` bloqueia publicação automática até atribuição (FR-003).
- `Desatualizado` sinaliza drift mas mantém a versão publicada anterior servida até aprovação (FR-016, edge case "fonte inacessível/obsoleta").
- `Expirado/Arquivado` é removido da indexação para resposta (FR-025).

## Índices e considerações de performance

- `Chunk.embedding`: índice vetorial (HNSW) no pgvector; consultas sempre com filtro ACL (`space_id`, `confidentiality`, e join a documento `state=published`) **antes** do operador de distância.
- Índices em `Document(space_id, state)`, `UpdateProposal(document_id, state)`, `AuditRecord(entity_type, entity_id, occurred_at)`, `SourceArtifact(connector_id, content_hash)`.
- Escala-alvo: ≤10k documentos, ≤~100k chunks, ≤500 usuários, ≤10 espaços (SC-009).
