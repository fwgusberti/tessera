# Phase 0 Research: Tessera

Decisões consolidadas para resolver as incógnitas técnicas. Formato: **Decisão / Justificativa / Alternativas consideradas**.

## 1. Busca vetorial: pgvector vs. vector DB dedicado

- **Decisão**: PostgreSQL 16 + extensão `pgvector` como único armazenamento (relacional + vetorial). Índice HNSW por padrão; filtro de ACL aplicado na cláusula `WHERE` **antes** do operador de distância vetorial.
- **Justificativa**: fonte única de verdade, consistência transacional entre `Document`/`Version`/`Chunk` e o vetor, operação simplificada no MVP (≤10k docs, ≤~100k chunks). Filtrar ACL no SQL antes do ANN evita pós-filtragem e vazamento de contexto a LLM.
- **Alternativas**: Pinecone/Weaviate/Qdrant (vector DB dedicado) — rejeitados no MVP por adicionar sincronização, custo operacional e risco de divergência ACL↔índice sem ganho na escala-alvo. Reavaliar acima de ~1M chunks.

## 2. RAG com permissões (ACL-first retrieval)

- **Decisão**: pipeline determinístico — (1) resolver permissões do solicitante (usuário humano ou credencial de agente) em conjunto de `space_id`/níveis de confidencialidade permitidos; (2) consulta pgvector filtrando `chunk.space_id IN (...) AND confidentiality <= permitido AND document.state = 'published'`; (3) montar contexto só com chunks recuperados; (4) gerar resposta com citações (IDs de chunk + versão); (5) se o melhor score < limiar configurável, responder "não sei" + dono do espaço.
- **Justificativa**: cumpre FR-008..FR-012, SC-004 e SC-007. Filtrar antes do ANN garante que conteúdo não permitido nunca entra no contexto enviado ao LLM externo.
- **Alternativas**: pós-filtrar resultados após recuperar tudo — rejeitado (risco de vazamento e desperdício). Reranker LLM dedicado — adiado; pode ser adicionado atrás do `LLMProvider` sem mudar o contrato.

## 3. Limiar de confiança / “não sei”

- **Decisão**: limiar configurável por espaço sobre o score de recuperação (similaridade do melhor chunk) **e** verificação de groundedness na resposta (LLM-as-judge). Default conservador definido na implementação; ajustável por administradores (Assumption da spec).
- **Justificativa**: SC-004 exige citação para afirmações e "não sei" quando cobertura insuficiente. Dois sinais (recuperação + groundedness) reduzem alucinação.
- **Alternativas**: limiar fixo global — rejeitado (espaços têm densidades diferentes de conteúdo).

## 4. Provider de LLM (abstração e modelos)

- **Decisão**: interface `LLMProvider` com implementação Anthropic (`anthropic` SDK). Modelos por tarefa, configuráveis:
  - Respostas do assistente e geração de propostas: `claude-opus-4-8` (padrão), com thinking adaptativo (`{"type": "adaptive"}`) e prompt caching do system prompt + contexto estável.
  - Classificação de drift: configurável para `claude-haiku-4-5` (custo); padrão seguro `claude-opus-4-8`.
  - Alternativa de alto volume sensível a custo para respostas: `claude-sonnet-4-6`.
- **Justificativa**: enunciado fixa Anthropic; abstração permite troca. Modelos atuais (2026-06): Opus 4.8 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5 por 1M tokens. IDs sem sufixo de data.
- **Alternativas**: acoplar diretamente ao SDK em cada serviço — rejeitado (viola Princípio II). `budget_tokens` para thinking — não usar (removido em Opus 4.8; usar thinking adaptativo).
- **Notas de API**: respostas longas usam streaming; citações nativas do Claude podem complementar a citação por chunk; nunca enviar documentos `restricted` ao provedor sem verificação de confidencialidade.

## 5. Provider de embeddings

- **Decisão**: interface `EmbeddingProvider` com implementação Voyage AI (família `voyage-3`). Dimensão do vetor fixada na migração do pgvector conforme o modelo escolhido; re-embedding versionado se o modelo mudar.
- **Justificativa**: enunciado sugere Voyage "ou similar"; Voyage é recomendado para embeddings de recuperação. Abstração permite troca.
- **Alternativas**: embeddings locais (sentence-transformers) — adiado; viável atrás da mesma interface se houver requisito de não enviar texto a terceiros para certos espaços.

## 6. Servidor MCP e autenticação de agentes

- **Decisão**: servidor MCP com o SDK oficial Python, expondo tools `search_documents` e `read_document`. Agentes autenticam com **tokens de serviço escopados por espaço**; o enforcement de permissões ocorre **no servidor** a cada chamada (reusa `core.permissions`). Documentos `restricted` ficam fora do índice exposto a agentes.
- **Justificativa**: FR-019/FR-020, SC-003, e a restrição "enforcement no servidor, nunca no cliente". Reuso de `core.permissions` garante paridade com o caminho humano.
- **Alternativas**: confiar em filtros do cliente — rejeitado (inseguro). Um único token global de serviço — rejeitado (sem granularidade por espaço).

## 7. Conectores como plugins

- **Decisão**: port `Connector` com método de sincronização que produz **eventos de mudança normalizados** (artefato, versão de origem, conteúdo markdown). MVP: conector Git/GitHub (READMEs, ADRs, markdown). Cada conector roda como job Celery agendado.
- **Justificativa**: FR-005..FR-007; testes de contrato garantem que qualquer conector futuro (Drive, Slack) cumpra o mesmo contrato.
- **Alternativas**: ingestão acoplada por fonte — rejeitado (não escala para múltiplas fontes da visão).

## 8. Pipeline de drift e human-in-the-loop

- **Decisão**: evento de mudança na fonte → diff semântico (embeddings para localizar documentos relacionados + LLM para classificar divergência material) → criação de `UpdateProposal` com patch em markdown → fila de revisão do dono do documento → publicação de nova versão **só após aprovação**. Se a fonte mudar de novo antes da aprovação, a proposta pendente é invalidada/atualizada.
- **Justificativa**: FR-013..FR-018, SC-002/SC-005. Garante que nenhuma atualização automática seja publicada sem aprovação humana.
- **Alternativas**: publicação automática com rollback — rejeitado (viola human-in-the-loop obrigatório do MVP).

## 9. AuthN/AuthZ e modelo de permissões

- **Decisão**: SSO via OIDC (Google Workspace no MVP). RBAC por espaço + nível de confidencialidade por documento. Grupos do IdP mapeados a setores/papéis; donos atribuídos por administradores. Decisão de acesso é uma função pura em `core.permissions`, reusada por `api` e `mcp-server`.
- **Justificativa**: FR-021/FR-022, SC-007; constituição (OAuth2/JWT). Função pura permite testes adversariais isolados.
- **Alternativas**: gestão interna de usuários — rejeitada na clarificação (escolhido SSO).

## 10. Versionamento, auditoria e ciclo de vida

- **Decisão**: `Version` imutável por documento (autor/aprovador/origem); estados de documento Ingerido → Sem dono → Publicado → Desatualizado → Expirado/Arquivado, com **apenas Publicado** indexável. Auditoria append-only para toda mudança de estado (ator, timestamp, entidade) — incluindo leituras de agentes (quem consultou o quê).
- **Justificativa**: FR-003a, FR-023/FR-024, SC-006. Append-only atende exigência de auditoria da constituição.
- **Alternativas**: histórico mutável/soft-delete — rejeitado (auditoria exige imutabilidade).

## 11. Observabilidade e métricas de produto

- **Decisão**: OpenTelemetry (traces + métricas) e logs estruturados. Métricas de produto (taxa de respostas corretas via LLM-as-judge contra conjunto de referência versionado, taxa de "não sei", documentos com drift, tempo até aprovação) expostas em dashboard interno.
- **Justificativa**: FR-026/FR-027, SC-008.
- **Alternativas**: apenas logs — insuficiente para SC-008.

## 12. Conformidade LGPD

- **Decisão**: minimização de dados em espaços de RH, registro de finalidade, suporte a direitos do titular (acesso/eliminação), retenção por política de espaço, e redação/expurgo de versões quando exigido.
- **Justificativa**: FR-025a; clarificação fixou LGPD como regime primário.
- **Alternativas**: sem regime formal — rejeitado na clarificação.

## Incógnitas remanescentes (não bloqueiam o MVP)

- Provedor de cloud de produção (adiado) e manifests Kubernetes — definidos na fase de hardening.
- Estratégia fina de chunking (tamanho/sobreposição) — calibrar empiricamente contra SC-001/SC-009; default razoável na implementação.
- Modelo/dimensão exata de embedding Voyage — fixar na migração; re-embedding versionado se mudar.
