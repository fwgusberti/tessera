# Feature Specification: Plataforma de Documentação Viva (Tessera)

**Feature Branch**: `001-living-docs-platform`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Plataforma de documentação viva para toda a empresa, consumida por humanos e por agentes de IA: ingere artefatos reais do trabalho via conectores, estrutura conhecimento por setor em espaços com donos e permissões, detecta drift entre fonte da verdade e documentação publicada gerando propostas de atualização aprovadas por humanos, e serve o conhecimento via busca semântica + assistente conversacional (para humanos) e API + servidor MCP (para agentes), com citações obrigatórias, controle de acesso granular, versionamento e auditoria."

## Clarifications

### Session 2026-06-12

- Q: Como a corretude das respostas é julgada e contra qual conjunto, para o critério "≥80% respondidas corretamente"? → A: Avaliação automatizada por LLM-as-judge contra um conjunto de respostas de referência (sem revisor humano).
- Q: Qual é o ciclo de vida canônico de um documento? → A: Estados explícitos — Ingerido → Sem dono → Publicado → Desatualizado (drift) → Expirado/Arquivado; apenas documentos no estado Publicado são indexáveis para resposta/citação.
- Q: Quais as metas de desempenho da experiência de resposta? → A: Busca semântica <2s (p95); início da resposta do assistente <5s (p95).
- Q: Qual o regime de conformidade alvo para dados pessoais/sensíveis (ex.: RH)? → A: LGPD (Brasil) como regime primário.
- Q: Quais as premissas de escala do MVP? → A: Moderada — até ~10k documentos, ~500 usuários e ~10 espaços.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conhecimento estruturado e ingerido por espaço (Priority: P1)

Um administrador conecta um repositório Git (READMEs, ADRs, documentos markdown) a um espaço setorial (ex.: Engenharia). O sistema ingere os artefatos, converte-os ao formato canônico (markdown + frontmatter de metadados: dono, setor, validade, tags, nível de confidencialidade) e os organiza dentro do espaço respeitando sua taxonomia. O espaço de RH é semeado da mesma forma a partir de um repositório de políticas em markdown ou por importação/criação direta de documentos.

**Why this priority**: Sem uma base de conhecimento estruturada e populada por espaço, nenhuma das demais capacidades (resposta, drift, MCP) entrega valor. É a fundação do produto e o pré-requisito do critério de sucesso "espaços de RH e Engenharia populados".

**Independent Test**: Conectar um repositório Git a um espaço, executar a ingestão e verificar que os documentos aparecem no espaço como markdown canônico com frontmatter completo, atribuídos ao setor e classificação corretos.

**Acceptance Scenarios**:

1. **Given** um repositório Git com READMEs e documentos markdown, **When** o administrador o conecta a um espaço e dispara a ingestão, **Then** cada artefato é publicado como documento canônico com frontmatter (dono, setor, validade, tags, confidencialidade) e associado ao espaço correto.
2. **Given** um documento ingerido sem dono identificável, **When** a ingestão conclui, **Then** o documento é marcado como "sem dono" e listado para atribuição pelo administrador antes de ficar elegível a publicação.
3. **Given** um documento em português e outro em inglês, **When** ambos são ingeridos, **Then** o idioma de cada documento é registrado nos metadados e ambos permanecem pesquisáveis.

---

### User Story 2 - Funcionário obtém resposta citada e respeitando permissões (Priority: P1)

Um novo funcionário pergunta em linguagem natural (ex.: "como solicito férias?" ou "como faço deploy em produção?") por busca semântica ou pelo assistente conversacional. O sistema responde com base apenas nos documentos a que o usuário tem acesso, cita as fontes usadas e, quando a confiança é baixa, responde "não sei" e sugere o dono do tópico em vez de inventar.

**Why this priority**: É a proposta de valor central para a maior base de usuários e a métrica-chave do MVP (≥80% das perguntas frequentes de onboarding respondidas corretamente com citação).

**Independent Test**: Com um espaço populado, fazer perguntas frequentes de onboarding com usuários de diferentes perfis e verificar que as respostas são corretas, citadas, restritas às permissões do usuário, e que perguntas sem cobertura retornam "não sei" com sugestão de dono.

**Acceptance Scenarios**:

1. **Given** um funcionário com acesso ao espaço de RH, **When** pergunta "como solicito férias?", **Then** recebe uma resposta correta com citação ao(s) documento(s)-fonte.
2. **Given** um funcionário sem acesso ao espaço de RH, **When** pergunta sobre uma política de RH confidencial, **Then** o sistema não revela o conteúdo nem a existência do documento restrito e não o usa como fonte.
3. **Given** uma pergunta sem cobertura suficiente na base acessível ao usuário, **When** o assistente avalia confiança baixa, **Then** responde "não sei" e sugere o dono do tópico/espaço correspondente.
4. **Given** qualquer resposta gerada pelo assistente, **When** ela é exibida, **Then** contém pelo menos uma citação rastreável ao documento-fonte e à sua versão.

---

### User Story 3 - Detecção de drift e atualização aprovada por humano (Priority: P2)

O sistema compara a fonte da verdade (ex.: conteúdo de um README/markdown no Git) com a documentação publicada e detecta divergência (drift). Ao detectar, gera uma proposta de atualização (edição pronta) e notifica o dono do documento, que revisa, aprova ou rejeita — em um fluxo tipo pull request. Nenhuma alteração é publicada sem aprovação humana.

**Why this priority**: É o diferencial que mantém a documentação "viva" e atende ao critério de sucesso de detecção de drift e ao requisito de human-in-the-loop obrigatório. Depende da base já existir (US1).

**Independent Test**: Alterar um arquivo na fonte conectada, executar a verificação de drift e confirmar que uma proposta de atualização é criada, atribuída ao dono, e que só altera o documento publicado após aprovação explícita.

**Acceptance Scenarios**:

1. **Given** um documento publicado derivado de uma fonte Git, **When** a fonte muda de forma materialmente divergente, **Then** o sistema registra drift detectado e cria uma proposta de atualização com a edição sugerida.
2. **Given** uma proposta de atualização pendente, **When** o dono do documento a aprova, **Then** uma nova versão é publicada e o histórico registra quem aprovou, quando e a partir de qual proposta.
3. **Given** uma proposta de atualização pendente, **When** o dono a rejeita, **Then** o documento publicado permanece inalterado e a rejeição é registrada com motivo opcional.
4. **Given** qualquer proposta gerada automaticamente, **When** nenhuma aprovação humana ocorreu, **Then** o conteúdo publicado e servido a humanos e agentes permanece na versão aprovada anterior.

---

### User Story 4 - Agente de IA consome conhecimento via MCP/API respeitando permissões (Priority: P2)

Um agente de IA externo (ex.: assistente de suporte) consulta a base via servidor MCP / API, recebendo conhecimento estruturado (markdown + metadados) com citações. O agente só acessa conteúdo permitido à identidade/credencial sob a qual opera, e perguntas sem cobertura retornam "não sei".

**Why this priority**: Cumpre a visão de servir IA como consumidor de primeira classe e o critério de sucesso "servidor MCP funcional consumido por pelo menos um agente externo respeitando permissões". Depende da base (US1).

**Independent Test**: Configurar uma credencial de agente com escopo limitado, consultar via MCP/API e verificar que o conteúdo retornado é estruturado, citado e restrito ao escopo permitido, com "não sei" para fora do escopo.

**Acceptance Scenarios**:

1. **Given** um agente autenticado com escopo no espaço de Engenharia, **When** consulta um tópico de Engenharia, **Then** recebe o conteúdo em markdown com metadados e citações às fontes.
2. **Given** o mesmo agente sem escopo no espaço de RH, **When** consulta um tópico de RH confidencial, **Then** o conteúdo restrito não é retornado nem referenciado.
3. **Given** uma consulta sem cobertura na base permitida ao agente, **When** a confiança é baixa, **Then** a resposta é "não sei" com indicação do dono/espaço sugerido.

---

### User Story 5 - Administração de espaços, conectores e permissões (Priority: P3)

Um administrador cria espaços por setor, configura conectores (Git no MVP), define permissões por setor/papel/documento mapeando grupos do provedor de identidade (SSO), designa donos e configura políticas de retenção.

**Why this priority**: É o painel de controle que habilita as demais histórias; sem ele a configuração seria estática. Tem prioridade menor porque, no MVP, a configuração inicial pode ser feita por um conjunto mínimo de operações de administração.

**Independent Test**: Como administrador, criar um espaço, conectar uma fonte Git, mapear um grupo de SSO a um papel/setor com um nível de acesso, e confirmar que usuários daquele grupo passam a ter exatamente o acesso configurado.

**Acceptance Scenarios**:

1. **Given** um administrador autenticado, **When** cria um espaço setorial e mapeia um grupo de SSO a um papel, **Then** os membros desse grupo recebem o nível de acesso definido para aquele espaço.
2. **Given** uma política de retenção configurada para um espaço, **When** um documento atinge o fim da validade definida, **Then** o sistema o sinaliza conforme a política (ex.: marcado como expirado e excluído da indexação para resposta).
3. **Given** uma alteração de permissão por um administrador, **When** ela é salva, **Then** a mudança passa a valer para consultas subsequentes de humanos e agentes e é registrada em auditoria.

---

### Edge Cases

- **Conteúdo conflitante entre documentos**: quando duas fontes acessíveis se contradizem, a resposta deve citar ambas e/ou sinalizar o conflito, sem escolher silenciosamente uma delas.
- **Documento sem dono**: propostas de drift sem aprovador são escaladas para o administrador do espaço.
- **Permissão negada vs. inexistente**: o sistema não deve revelar a existência de um documento restrito a quem não tem acesso (negar sem vazar metadados).
- **Mudança de permissão durante uma sessão/consulta**: respostas refletem as permissões vigentes no momento da consulta.
- **Fonte conectada removida ou inacessível**: documentos derivados permanecem na última versão aprovada e a falha de sincronização é sinalizada, sem despublicar conteúdo.
- **Pergunta em idioma diferente do documento-fonte**: a resposta deve ser compreensível para o usuário e ainda citar a fonte original.
- **Proposta de drift obsoleta**: se a fonte muda novamente antes da aprovação, a proposta pendente é atualizada ou invalidada para não publicar conteúdo desatualizado.
- **Conteúdo confidencial em citação**: a citação nunca pode expor trechos de documentos a que o solicitante não tem acesso.

## Requirements *(mandatory)*

### Functional Requirements

#### Espaços e estrutura de conhecimento

- **FR-001**: O sistema MUST permitir criar e gerenciar espaços separados por setor (ex.: Engenharia, RH, Operações, Vendas), cada um com sua taxonomia, donos e regras de acesso próprias.
- **FR-002**: O sistema MUST armazenar todo documento publicado em formato canônico markdown com frontmatter de metadados contendo, no mínimo: dono, setor/espaço, validade, tags, nível de confidencialidade e idioma.
- **FR-003**: O sistema MUST associar cada documento a exatamente um espaço e a um dono responsável; documentos sem dono MUST ser sinalizados e bloqueados de publicação automática até atribuição.
- **FR-003a**: O sistema MUST gerenciar o ciclo de vida de cada documento por meio dos estados Ingerido → Sem dono → Publicado → Desatualizado → Expirado/Arquivado, e MUST indexar para resposta e citação apenas documentos no estado Publicado.
- **FR-004**: O sistema MUST suportar conteúdo multilíngue, no mínimo português e inglês, registrando o idioma de cada documento.

#### Ingestão e conectores

- **FR-005**: O sistema MUST ingerir artefatos de repositórios Git (READMEs, ADRs e documentos markdown) e convertê-los ao formato canônico, preservando rastreabilidade até a fonte original.
- **FR-006**: O sistema MUST permitir vincular uma fonte conectada a um espaço específico e disparar ou agendar sincronizações de ingestão.
- **FR-007**: O sistema MUST registrar a origem (fonte, localização e versão/identificador do artefato) de cada documento derivado de um conector.

#### Resposta a humanos (busca + assistente)

- **FR-008**: O sistema MUST oferecer busca semântica sobre o conhecimento acessível ao usuário.
- **FR-009**: O sistema MUST oferecer um assistente conversacional que responde a perguntas em linguagem natural usando apenas documentos a que o usuário tem acesso.
- **FR-010**: Toda resposta do assistente MUST incluir citações rastreáveis aos documentos-fonte e às respectivas versões.
- **FR-011**: Quando a confiança na resposta for baixa, o sistema MUST responder "não sei" e sugerir o dono do tópico/espaço, em vez de produzir resposta não fundamentada.
- **FR-012**: O sistema MUST impedir que respostas, citações ou sugestões revelem conteúdo, trechos ou a existência de documentos aos quais o solicitante não tem acesso.

#### Detecção de drift e aprovação humana

- **FR-013**: O sistema MUST detectar drift comparando a fonte da verdade conectada (no MVP, fontes Git) com a documentação publicada correspondente.
- **FR-014**: Ao detectar drift, o sistema MUST gerar uma proposta de atualização com a edição sugerida e notificar o dono do documento.
- **FR-015**: O dono MUST poder aprovar ou rejeitar cada proposta; rejeições MUST permitir registro de motivo.
- **FR-016**: O sistema MUST NOT publicar nenhuma atualização gerada automaticamente sem aprovação humana explícita (human-in-the-loop obrigatório no MVP).
- **FR-017**: O sistema MUST escalar para o administrador do espaço propostas cujo documento não tenha dono atribuído.
- **FR-018**: O sistema MUST invalidar ou atualizar propostas pendentes quando a fonte da verdade mudar novamente antes da aprovação.

#### Interface para agentes (API/MCP)

- **FR-019**: O sistema MUST expor o conhecimento a agentes de IA via API e via servidor MCP, retornando conteúdo estruturado (markdown + metadados) com citações.
- **FR-020**: O acesso de agentes MUST ser restrito ao escopo de permissões da credencial/identidade sob a qual o agente opera, com o mesmo comportamento de "não sei" para conteúdo fora do escopo.

#### Controle de acesso, identidade e auditoria

- **FR-021**: O sistema MUST autenticar usuários por meio de um provedor de identidade externo (SSO) e mapear grupos do provedor a setores/papéis.
- **FR-022**: O sistema MUST aplicar controle de acesso granular por setor, papel e documento, garantindo que documentos sensíveis (ex.: RH) nunca sejam expostos a setores ou agentes sem permissão.
- **FR-023**: O sistema MUST manter versionamento completo de cada documento, com histórico de mudanças e capacidade de consultar versões anteriores.
- **FR-024**: O sistema MUST registrar auditoria de toda ação de mudança de estado (publicação, aprovação, rejeição, alteração de permissão, ingestão), incluindo ator, data/hora e entidade afetada.
- **FR-025**: O administrador MUST poder configurar políticas de retenção e validade por espaço, e o sistema MUST sinalizar/agir sobre documentos expirados conforme a política (incluindo removê-los da indexação para resposta).
- **FR-025a**: O tratamento de dados pessoais/sensíveis (especialmente em espaços de RH) MUST estar em conformidade com a LGPD, incluindo minimização de dados, registro de finalidade de tratamento, suporte aos direitos do titular (ex.: acesso e eliminação) e retenção limitada ao necessário.

#### Métricas de qualidade

- **FR-026**: O sistema MUST medir e expor métricas orientadas a resultado: taxa de perguntas respondidas corretamente, taxa de "não sei", documentos com drift detectado e tempo até aprovação de atualizações.
- **FR-027**: O sistema MUST avaliar a corretude das respostas de forma automatizada (LLM-as-judge), comparando a resposta gerada e suas citações a um conjunto versionado de respostas de referência mantido por espaço, sem exigir revisor humano para o cálculo da métrica.

### Key Entities *(include if feature involves data)*

- **Espaço (Space)**: agrupamento setorial de conhecimento; possui taxonomia, donos, regras de acesso e políticas de retenção.
- **Documento (Document)**: unidade canônica de conhecimento em markdown com frontmatter; pertence a um espaço, tem um dono, nível de confidencialidade, idioma, validade e tags; possui múltiplas versões e um estado de ciclo de vida (Ingerido, Sem dono, Publicado, Desatualizado, Expirado/Arquivado).
- **Versão de Documento (Document Version)**: estado imutável de um documento em um ponto no tempo, com autor/aprovador e origem.
- **Fonte/Conector (Source/Connector)**: configuração de ingestão a partir de um sistema externo (Git no MVP), vinculada a um espaço.
- **Artefato de Origem (Source Artifact)**: item bruto ingerido de uma fonte (README, ADR, arquivo markdown) com identificador de versão da fonte.
- **Proposta de Atualização (Update Proposal)**: edição sugerida derivada de drift, com estado (pendente/aprovada/rejeitada), documento alvo, aprovador e motivo.
- **Usuário (User)**: identidade autenticada via SSO, com pertencimento a grupos/setores e papéis.
- **Papel/Permissão (Role/Permission)**: definição de nível de acesso por setor/papel/documento, mapeada de grupos do provedor de identidade.
- **Credencial de Agente (Agent Credential)**: identidade não-humana com escopo de acesso para consumo via API/MCP.
- **Registro de Auditoria (Audit Record)**: evento de mudança de estado com ator, data/hora e entidade afetada.
- **Citação (Citation)**: referência rastreável de uma resposta a um documento-fonte e sua versão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um espaço de RH e um de Engenharia estão populados, e ≥80% das perguntas frequentes de onboarding são respondidas corretamente e com citação às fontes. A corretude é medida por avaliação automatizada (LLM-as-judge) contra um conjunto versionado de respostas de referência por espaço.
- **SC-002**: A detecção de drift funciona para ao menos um tipo de fonte (mudança em README/markdown no Git): uma alteração relevante na fonte gera uma proposta de atualização atribuída ao dono.
- **SC-003**: Um servidor MCP funcional é consumido por ao menos um agente externo, e esse agente nunca recebe conteúdo fora do seu escopo de permissão (0 vazamentos em testes de permissão).
- **SC-004**: 100% das respostas do assistente que afirmam um fato incluem ao menos uma citação rastreável; respostas sem cobertura suficiente retornam "não sei" em vez de conteúdo não fundamentado.
- **SC-005**: 100% das atualizações publicadas a partir de drift passaram por aprovação humana registrada (zero publicações automáticas sem aprovação).
- **SC-006**: 100% das ações de mudança de estado possuem registro de auditoria com ator, data/hora e entidade afetada, e todo documento publicado mantém histórico de versões consultável.
- **SC-007**: Em testes de permissão entre setores, documentos confidenciais (ex.: RH) não são expostos — nem conteúdo, nem citação, nem existência — a usuários ou agentes sem acesso (0 vazamentos).
- **SC-008**: As métricas de qualidade (perguntas corretas, taxa de "não sei", documentos com drift, tempo até aprovação) estão disponíveis para os administradores ao final do MVP.
- **SC-009**: A busca semântica retorna resultados em menos de 2 segundos (p95) e o assistente começa a apresentar a resposta em menos de 5 segundos (p95), sob carga representativa do MVP (até ~10k documentos, ~500 usuários, ~10 espaços).

## Assumptions

- **Escopo de conectores no MVP**: apenas Git (repositórios com READMEs, ADRs e markdown). Slack/Teams, Jira/Linear, Google Drive, CRMs e ferramentas de operações pertencem à visão futura e estão fora do MVP. O espaço de RH é semeado a partir de um repositório Git de políticas em markdown ou por importação/criação direta de documentos.
- **Identidade e permissões**: a autenticação usa um provedor de identidade externo (SSO); o sistema mapeia grupos do provedor a setores/papéis. A atribuição fina de donos por documento pode ser curada por administradores.
- **Assistente conversacional no MVP**: o assistente com citações e comportamento "não sei" faz parte do MVP, junto da busca semântica e do MCP/API.
- **Tessera é o sistema de registro dos documentos publicados**: o conteúdo canônico vive no Tessera (markdown + frontmatter); os conectores alimentam ingestão e detecção de drift, mas a publicação é controlada dentro da plataforma.
- **Uso interno**: o foco é interno à empresa; publicação externa para clientes está fora de escopo.
- **Fora de escopo (confirmado)**: edição colaborativa em tempo real estilo Google Docs; geração de documentação a partir de áudio/vídeo de reuniões; publicação externa.
- **Limiar de confiança configurável**: o ponto de corte que dispara "não sei" é um parâmetro ajustável pelos administradores, com um padrão razoável definido na implementação.
- **Idiomas**: português e inglês são suportados no MVP; outros idiomas ficam para depois.
- **Escala-alvo do MVP**: dimensionado para até ~10 mil documentos, ~500 usuários e ~10 espaços; escalas maiores ficam para fases futuras.
- **Conformidade**: LGPD é o regime primário no MVP; outros regimes (ex.: GDPR) ficam para quando houver operação internacional.
