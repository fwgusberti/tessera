# Contract: Connector (plugin de ingestão)

Port `Connector` definido em `core.ports`. Cada fonte externa implementa este contrato; o MVP entrega a implementação **Git/GitHub**. Conectores rodam como jobs Celery agendados e produzem **eventos de mudança normalizados** — desacoplando ingestão e detecção de drift da fonte específica.

## Interface (lógica)

```
Connector:
  fetch_changes(since: SyncCursor | None) -> ChangeBatch
  # Retorna artefatos novos/alterados desde o último cursor.

ChangeBatch:
  cursor: SyncCursor                 # opaco; persistido em Connector.last_sync
  artifacts: list[NormalizedArtifact]

NormalizedArtifact:
  external_id: str                   # id estável na fonte (ex.: caminho do arquivo)
  source_version: str                # ex.: commit SHA
  path: str
  content_markdown: str              # conteúdo já normalizado para markdown
  suggested_frontmatter: dict        # dono/idioma/tags inferidos quando possível
  content_hash: str                  # para detectar mudança/drift (FR-007)
  fetched_at: datetime
```

## Regras do contrato
- **Normalização**: a saída é sempre markdown (nunca HTML proprietário) com frontmatter sugerido; campos não inferíveis ficam vazios para atribuição humana.
- **Rastreabilidade**: `external_id` + `source_version` + `content_hash` permitem ligar `SourceArtifact` → `DocumentVersion` e detectar drift (FR-005/FR-007/FR-013).
- **Idempotência**: reprocessar o mesmo `source_version` não cria versões duplicadas (compara `content_hash`).
- **Sem dono ⇒ bloqueio**: artefato sem dono identificável gera documento em estado `Sem dono`, não publicável até atribuição (FR-003).
- **Segredos**: credenciais da fonte vêm por referência a segredo injetado no ambiente; nunca em `config` em texto.
- **Idioma**: idioma detectado/registrado por artefato (FR-004).

## Implementação MVP: Git/GitHub
- Config: `{ repo_url, branch, credential_ref, include_globs?: ["**/*.md","**/README*","**/adr/**"] }`.
- `fetch_changes` usa o diff de commits desde o `source_version` do cursor; `source_version` = commit SHA.
- READMEs, ADRs e arquivos markdown viram `NormalizedArtifact` (markdown já é o formato nativo).

## Testes de contrato (obrigatórios, por conector)
- **Forma do output**: `fetch_changes` retorna `ChangeBatch` com artefatos válidos (markdown + hash + source_version).
- **Idempotência**: segunda sincronização sem mudança na fonte ⇒ 0 novos artefatos materiais.
- **Detecção de mudança**: alterar um arquivo na fonte ⇒ artefato com novo `content_hash` e `source_version` (alimenta o pipeline de drift — SC-002).
- **Sem dono**: artefato sem dono ⇒ documento bloqueado de publicação automática.
- **Segredo**: nenhum segredo em texto no `config` persistido.
