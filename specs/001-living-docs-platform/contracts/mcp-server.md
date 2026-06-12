# Contract: Servidor MCP (agentes de IA)

Aplicação `mcp-server` usando o SDK oficial de MCP em Python. Expõe o conhecimento a agentes externos (Claude, Copilot, agentes internos) como tools estruturadas. **Enforcement de permissões no servidor, nunca no cliente.**

## Autenticação
- Agente apresenta um **token de serviço escopado por espaço** (`AgentCredential`).
- O servidor resolve `scoped_space_ids` + `max_confidentiality` da credencial a cada chamada e aplica o mesmo `core.permissions` usado pela API humana.
- Documentos `restricted` ficam **fora** do índice exposto a agentes, independentemente do escopo.
- Toda chamada registra `AuditRecord` (`actor_type=agent`, action=`query`/`read`, entidade consultada) — "qual agente consultou o quê".

## Tools expostas

### `search_documents`
Busca semântica sobre o conhecimento permitido à credencial.
- **Input**: `{ query: string, space_ids?: string[], language?: "pt-BR"|"en", top_k?: number }`
- **Output**: `{ results: [{ document_id, version_id, chunk_id, score, snippet, citation: { document_title, source } }] }`
- **Regras**: filtra ACL **antes** da busca vetorial; só `published`; nunca retorna chunk de espaço/confidencialidade fora do escopo. Se `space_ids` incluir espaço fora do escopo, ignora-o silenciosamente (não vaza existência).

### `read_document`
Lê o conteúdo canônico (markdown + metadados) de um documento permitido.
- **Input**: `{ document_id: string, version?: number }`
- **Output**: `{ document_id, title, markdown, frontmatter, version_number, citations_supported: true }`
- **Regras**: 404-equivalente (erro `not_found`) se o documento não for permitido à credencial — não distingue "inexistente" de "sem permissão" (SC-007). `restricted` nunca legível por agente.

## Comportamento de baixa confiança
- Quando a recuperação não atinge o limiar, `search_documents` retorna lista vazia e o servidor inclui uma sugestão estruturada `{ dont_know: true, suggested_owner }` para o espaço relevante (paridade com o assistente humano — FR-020).

## Testes de contrato (obrigatórios)
- **Escopo**: credencial com escopo só em Engenharia consulta tópico de RH `restricted`/confidencial ⇒ 0 resultados e nenhum vazamento de existência (SC-003/SC-007).
- **Paridade de permissões**: dado o mesmo conjunto de permissões, `search_documents` retorna o mesmo conjunto de documentos que o `POST /v1/search` da API humana (reuso de `core.permissions`).
- **Auditoria**: cada chamada produz exatamente um `AuditRecord` com a credencial e a entidade consultada.
- **Estrutura**: output sempre markdown + metadados + citação rastreável (FR-019).
