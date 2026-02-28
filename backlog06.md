## Plano de refatoração (MVP) — Sala de Interrogatório

A proposta deste plano é **corrigir o que quebra o loop de investigação** sem transformar o projeto em um redesign completo. O foco é refatorar com segurança, manter a arquitetura atual (FastAPI + SQLAlchemy + SQLite + adapters de IA) e aumentar a integridade do gameplay.

---

# 1) Princípios de refatoração (MVP)

### Objetivo do plano

Preservar o MVP como **jogo de interrogatório guiado por evidências**, eliminando:

* bypass do loop principal,
* vazamento de meta-informação,
* inconsistências de estado,
* feedback falso ao jogador.

### Princípios adotados

1. **Corrigir integridade antes de adicionar feature**

   * Primeiro garantir que o loop atual funcione corretamente.
2. **Refatoração incremental**

   * Mudanças pequenas, testáveis e reversíveis.
3. **Compatibilidade controlada de API**

   * Quando quebrar contrato, versionar ou introduzir transição.
4. **Backend soberano**

   * Cliente não define estado “válido” do jogo.
5. **Telemetria/testes antes de otimização**

   * Priorizar confiabilidade e regressão.
6. **MVP ≠ protótipo frágil**

   * MVP pode ser simples, mas precisa ser consistente.

---

# 2) Roadmap de execução (por fases)

## Fase 1 — Integridade do loop (P0)

Corrigir tudo que permite vencer sem jogar ou gera estado inconsistente.

* Turno atômico de interrogatório
* Bloqueio de sessão finalizada
* Validação de inputs de acusação
* Remoção de spoilers (`is_mandatory`)
* Acusação baseada em evidências realmente usadas/confirmadas

## Fase 2 — Qualidade da resposta e consistência narrativa (P1)

Corrigir bugs de feedback e reduzir risco da IA contradizer o design.

* Dummy adapter sem falso positivo
* Prompt sem duplicação
* Separar `personality` de `backstory`
* Reduzir contexto oculto enviado ao LLM

## Fase 3 — Robustez de conteúdo e manutenção (P1/P2)

Melhorar pipeline de cenário, testes e documentação.

* Loader transacional
* Regras de progresso/fechamento consistentes
* Testes de regressão do loop
* Documentação de contrato da API

---

# 3) Backlog detalhado (com contexto, melhores práticas e DoD)

Abaixo, cada tarefa foi escrita para poder ser executada sem depender do contexto geral.

---

## EPIC A — Integridade do turno e estado de sessão (P0)

---

### Tarefa A1 — Tornar o turno de interrogatório atômico (uma única transação DB)

**Prioridade:** P0
**Tipo:** Refatoração backend / integridade transacional
**Impacto:** Alto (estado do jogo)

### Contexto (autossuficiente)

Hoje o endpoint `POST /sessions/{session_id}/suspects/{suspect_id}/messages` executa o turno em etapas separadas:

* salva mensagem do jogador (`add_player_message`)
* aplica evidência (`apply_evidence_to_suspect`)
* gera resposta do NPC (`add_npc_reply`)
* busca estado (`get_suspect_state`)

Cada serviço pode abrir/fechar sua própria sessão SQLAlchemy e fazer `commit()` próprio. Isso cria risco de **estado parcial** (ex.: mensagem salva, mas resposta do NPC falha; evidência aplicada sem resposta; progresso alterado sem turn completo).

Para um jogo investigativo, o turno precisa ser tratado como **unidade indivisível**.

### Objetivo

Garantir que um turno completo de interrogatório seja persistido de forma **atômica**:

* ou tudo persiste,
* ou nada persiste.

### Escopo

* Refatorar endpoint `send_message_to_suspect` para usar **uma única sessão SQLAlchemy**.
* Passar `db` explicitamente para todos os serviços envolvidos.
* Realizar `commit()` final apenas uma vez no fluxo.
* Em caso de erro, `rollback()` e retornar erro apropriado.

### Fora de escopo (MVP)

* Trocar ORM
* Implementar fila assíncrona para IA
* Retry automático de provider de IA

### Arquivos impactados (prováveis)

* `app/api/sessions.py`
* `app/services/chat_service.py`
* `app/services/secret_service.py`
* `app/services/session_service.py`

### Subtarefas técnicas

1. Criar um serviço de orquestração de turno (ex.: `interrogation_turn_service.py`) com assinatura:

   * `run_interrogation_turn(session_id, suspect_id, text, evidence_id, db)`
2. Mover a sequência de chamadas do endpoint para esse serviço.
3. Garantir que `add_player_message`, `apply_evidence_to_suspect`, `add_npc_reply` **não façam commit final** quando `db` for externo.
4. Padronizar retorno serializável do turno.
5. No endpoint, capturar exceções e mapear para `HTTPException`.

### Melhores práticas obrigatórias

* Usar `try/except/finally` com `db.rollback()` em erro.
* Não misturar regra de negócio com serialização HTTP.
* Não retornar ORM para camada API.

### DoD (Definition of Done)

* [ ] Um erro no passo de IA não deixa mensagem do jogador persistida isoladamente.
* [ ] Um erro na aplicação de evidência não altera progresso/segredos parcialmente.
* [ ] Existe teste de integração cobrindo rollback do turno.
* [ ] Endpoint continua retornando resposta serializável compatível (ou contrato versionado).
* [ ] Código com commits centralizados (sem commit espalhado no fluxo do turno).

---

### Tarefa A2 — Bloquear interações em sessão finalizada

**Prioridade:** P0
**Tipo:** Regra de negócio / integridade do loop
**Impacto:** Alto

### Contexto

Após `POST /sessions/{session_id}/accuse`, a sessão é marcada como `finished`, mas o código atual ainda permite novas mensagens de interrogatório. Isso quebra a semântica do ciclo do jogo (investigação → acusação → encerramento).

### Objetivo

Impedir qualquer ação de progresso em sessão com status `finished`.

### Escopo

* Bloquear:

  * `POST /sessions/{session_id}/suspects/{suspect_id}/messages`
  * qualquer endpoint futuro que altere progresso/estado
* Retornar erro de domínio consistente (`409 Conflict` recomendado)

### Fora de escopo

* Reabrir sessão
* Modo pós-jogo com interrogatório livre

### Arquivos impactados

* `app/api/sessions.py`
* `app/services/chat_service.py` (ou serviço de turno)
* `app/services/session_finalize_service.py` (apenas referência de status)

### Subtarefas técnicas

1. Validar status da sessão no início do turno.
2. Criar mensagem de erro padronizada (ex.: `"Session is already finished"`).
3. Garantir que o bloqueio exista na camada de serviço, não apenas na API.

### Melhores práticas

* Validar regra crítica na camada de domínio/serviço.
* Não depender exclusivamente da UI para bloquear ação.

### DoD

* [ ] Não é possível enviar mensagem para suspeito após acusação final.
* [ ] Erro retorna status HTTP consistente (409 ou 400, conforme padrão definido).
* [ ] Existe teste de integração cobrindo tentativa de jogar após sessão finalizada.
* [ ] Nenhuma alteração é persistida em DB nessa tentativa.

---

### Tarefa A3 — Normalizar tratamento de erros de domínio → HTTP

**Prioridade:** P0
**Tipo:** API / ergonomia / observabilidade
**Impacto:** Alto (cliente e debug)

### Contexto

Vários serviços lançam `ValueError` (sessão inexistente, suspeito inválido, evidência inválida), mas nem todos os endpoints convertem isso para `HTTPException`. Isso pode gerar `500 Internal Server Error` para erros de regra do jogo.

### Objetivo

Padronizar conversão de erros de domínio em respostas HTTP previsíveis.

### Escopo

* Criar classe(s) de exceção de domínio (ex.: `DomainError`, `NotFoundError`, `RuleViolationError`)
* Mapear para status HTTP adequados
* Aplicar no endpoint de mensagens, acusação e endpoints de leitura que hoje estão inconsistentes

### Fora de escopo

* Sistema global de i18n de erros
* Catálogo de erro com códigos públicos completos

### Arquivos impactados

* `app/api/sessions.py`
* `app/api/scenarios.py`
* `app/services/*` (gradualmente)
* possivelmente novo `app/core/exceptions.py`

### Subtarefas técnicas

1. Definir exceções de domínio.
2. Substituir `ValueError` nos serviços críticos P0.
3. Adicionar handler global FastAPI (opcional no MVP) ou mapear no endpoint.
4. Garantir mensagens úteis para UI/log.

### Melhores práticas

* Erro de input/jogada inválida ≠ erro interno.
* Não vazar stack trace para cliente.

### DoD

* [ ] Erros de regra (sessão não existe, suspeito inválido, evidência inválida) não retornam 500.
* [ ] Contratos de erro são consistentes entre endpoints.
* [ ] Testes cobrem ao menos 5 cenários de erro de domínio.
* [ ] Logs internos preservam causa técnica.

---

## EPIC B — Integridade da acusação e anti-bypass (P0)

---

### Tarefa B1 — Remover spoilers de veredito dos endpoints públicos (`is_mandatory`) - CONCLUÍDO

**Prioridade:** P0
**Tipo:** Game design + API contract
**Impacto:** Crítico para o loop investigativo

### Contexto

Os endpoints de cenário/sessão expõem `is_mandatory` por evidência. Isso revela ao jogador quais evidências contam para o veredito final, eliminando parte da dedução e transformando a acusação em checklist.

### Objetivo

Parar de expor ao cliente quais evidências são obrigatórias para o veredito.

### Escopo

* Remover `is_mandatory` de:

  * `GET /scenarios/{scenario_id}`
  * `GET /sessions/{session_id}/evidences`
* Se necessário, criar flag de compatibilidade temporária (ex.: config dev-only)

### Fora de escopo

* Mudar modelo interno de `required_evidence_ids`
* Redesenhar o sistema de evidências

### Arquivos impactados

* `app/api/scenarios.py`
* `app/api/sessions.py`
* `app/api/schemas/evidence.py`
* `app/api/schemas/scenario.py`
* clientes/frontend que consumirem o campo

### Subtarefas técnicas

1. Remover campo dos schemas de resposta públicos.
2. Ajustar serialização nos endpoints.
3. Atualizar README/API docs.
4. Ajustar testes que esperam esse campo.

### Melhores práticas

* Regras internas de vitória devem permanecer no backend.
* Expor apenas informação necessária à decisão do jogador.

### DoD

* [x] Nenhum endpoint de jogador expõe `is_mandatory`.
* [x] Documentação atualizada sem esse campo (será feito na tarefa final de docs).
* [x] Testes de contrato de API ajustados (ou confirmados não falhos).
* [x] Veredito interno continua funcionando sem alteração de regra.

---

### Tarefa B2 — Validar `suspect_id` e `evidence_ids` da acusação contra o cenário da sessão

**Prioridade:** P0
**Tipo:** Validação de domínio
**Impacto:** Alto

### Contexto

`evaluate_verdict()` avalia a acusação sem validar se:

* o `chosen_suspect_id` pertence ao cenário da sessão,
* os `evidence_ids` enviados pertencem ao cenário da sessão.

Isso permite payload inválido entrar na lógica de veredito.

### Objetivo

Garantir que a acusação só aceite entidades pertencentes ao cenário da sessão.

### Escopo

* Validar suspeito e evidências no `finalize_session` ou `evaluate_verdict`
* Retornar erro de domínio se houver IDs inválidos

### Fora de escopo

* Validação de coerência narrativa da acusação
* Interface de seleção guiada no frontend

### Arquivos impactados

* `app/services/session_finalize_service.py`
* `app/services/verdict_service.py`
* `app/infrastructure/db_models.py` (somente consulta, sem mudança necessária)

### Subtarefas técnicas

1. Carregar `session -> scenario`.
2. Validar suspeito contra `SuspectModel.scenario_id`.
3. Validar todos os `evidence_ids` contra `EvidenceModel.scenario_id`.
4. Rejeitar duplicatas de `evidence_ids` (recomendado no MVP).
5. Cobrir cenários de erro em teste.

### Melhores práticas

* Validar input externo antes da regra final.
* Fail fast com mensagem clara.

### DoD

* [x] **B2: Validação de IDs da acusação:** Validar `suspect_id` e itens em `evidence_ids` contra o `scenario_id` da sessão.

---

### Tarefa B3 — Exigir evidências “confirmadas na sessão” para a acusação final

**Prioridade:** P0
**Tipo:** Game rule / anti-bypass
**Impacto:** Crítico

### Contexto

Hoje o jogador pode enviar qualquer lista de `evidence_ids` em `/accuse`, mesmo sem nunca usar essas evidências nos interrogatórios. Isso permite vencer sem passar pelo loop principal.

A regra mínima necessária para o MVP é: **só pode acusar usando evidências que foram realmente trabalhadas durante a sessão**.

### Objetivo

Restringir a acusação final a evidências que tenham sido ao menos:

* usadas em confronto na sessão, e idealmente
* marcadas como “efetivas” (revelaram algo)

### Escopo (MVP recomendado)

* Implementar validação por evidências **usadas na sessão** (mínimo)
* Opcional P1: subir régua para evidências **efetivas/confirmadas**

### Fora de escopo

* Sistema completo de “descoberta” de evidências
* Montagem textual de tese acusatória

### Arquivos impactados

* `app/services/verdict_service.py`
* `app/infra/db_models.py` (uso da tabela `SessionEvidenceUsageModel`)
* `app/services/chat_service.py` (já registra uso)
* `app/services/secret_service.py` (para versão “effective”)

### Subtarefas técnicas

1. Buscar conjunto de evidências usadas na sessão (`session_evidence_usages`).
2. Validar que todas as evidências da acusação pertencem a esse conjunto.
3. Definir comportamento:

   * rejeitar acusação inválida (`400/409`)
   * ou ignorar evidências não usadas (não recomendado)
4. Atualizar descrição de veredito/documentação.

### Melhores práticas

* Regra de vitória deve depender do histórico de jogo, não só do payload final.
* Regras críticas devem ser determinísticas e testáveis sem IA.

### DoD

* [ ] Não é possível vencer com evidências nunca usadas na sessão.
* [ ] Regra está coberta por testes de integração.
* [ ] README/API docs explicam a nova regra.
* [ ] A IA continua sendo irrelevante para a validação (backend soberano).

---

### Tarefa B4 — Registrar efetividade da evidência por turno/suspeito (base para regra de acusação e UX) - CONCLUÍDO

**Prioridade:** P0/P1 (P0 se usada na acusação; P1 se só telemetria)
**Tipo:** Modelo de dados / rastreabilidade
**Impacto:** Alto

### Contexto

Existe `SessionEvidenceUsageModel`, que registra que uma evidência foi usada contra um suspeito. Mas não diferencia:

* uso sem efeito,
* uso que revelou segredo,
* uso repetido.

Sem isso, a acusação e o feedback do jogo ficam fracos.

### Objetivo

Persistir **resultado da aplicação da evidência** de forma explícita.

### Escopo (MVP simples)

Adicionar campos em `SessionEvidenceUsageModel` **ou** nova tabela de evento de confronto:

* `was_effective: bool`
* `revealed_secret_ids_snapshot` (opcional JSON)
* `last_used_at` / `use_count` (opcional)

**Recomendação MVP:** manter mesma tabela e adicionar `was_effective` + `used_at` atualizado.

### Fora de escopo

* Telemetria avançada
* Analytics por funil de jogadores

### Arquivos impactados

* `app/infra/db_models.py`
* migração/estratégia de schema (se sem Alembic, script manual MVP)
* `app/services/chat_service.py`
* `app/services/secret_service.py`

### Subtarefas técnicas

1. Definir schema mínimo (`was_effective`).
2. Atualizar lógica de uso:

   * se `apply_evidence_to_suspect` revelou algo novo => `was_effective = True`
3. Tratar reuso de mesma evidência (não sobrescrever efetividade para `False` depois de `True`).
4. Expor isso internamente para veredito/UX (não necessariamente endpoint público já).

### Melhores práticas

* Persistir fatos de gameplay explícitos, não inferir depois via heurística.
* Evitar reprocessar histórico de chat para decidir validade.

### DoD

* [x] Cada uso de evidência tem registro confiável de efetividade (mínimo uma vez por par sessão/suspeito/evidência).
* [x] Reuso da mesma evidência não perde informação.
* [x] Testes cobrem uso efetivo e inefetivo.
* [x] Preparado para regra futura “acusação só com evidências efetivas”.

---

## EPIC C — Consistência de feedback e IA (P1)

---

### Tarefa C1 — Corrigir falso positivo do Dummy AI (usar `revealed_now`, não `revealed_secrets` acumulado) - CONCLUÍDO

**Prioridade:** P1
**Tipo:** Bug de gameplay / feedback
**Impacto:** Alto para testes e percepção do jogador

### Contexto

No fluxo atual, `add_npc_reply` monta `suspect_state["revealed_secrets"]` com **todos** os segredos já revelados ao suspeito naquela sessão. O `DummyNpcAIAdapter` usa isso para reagir a qualquer `evidence_id`, o que pode gerar resposta de “essa evidência me incrimina” mesmo quando a evidência atual não revelou nada novo.

Isso induz o jogador a conclusões erradas e invalida testes de feedback.

### Objetivo

Fazer o Dummy responder com base nos **segredos revelados neste turno** (`revealed_now`) e não no acumulado histórico.

### Escopo

* Passar `revealed_now` ao adapter (em `player_message` ou `npc_context`)
* Atualizar `DummyNpcAIAdapter.generate_reply()`

### Fora de escopo

* Melhorar qualidade literária das respostas
* Sistema emocional complexo de NPC

### Arquivos impactados

* `app/services/chat_service.py`
* `app/services/ai_adapter_dummy.py`
* possivelmente `app/services/ai_adapter.py` (documentação da interface)

### Subtarefas técnicas

1. Capturar retorno de `apply_evidence_to_suspect` como `revealed_now`.
2. Encaminhar `revealed_now` ao adapter.
3. Alterar dummy para:

   * resposta incriminadora somente se `revealed_now` não vazio
   * resposta defensiva se evidência não teve efeito
4. Criar teste de regressão do bug.

### Melhores práticas

* Feedback do sistema deve refletir o evento atual, não estado acumulado ambíguo.
* Dummy adapter deve ser confiável para testes automatizados.

### DoD

* [ ] Evidência sem efeito não gera resposta de admissão/incriminação no dummy.
* [ ] Evidência com efeito gera resposta apropriada.
* [ ] Existe teste cobrindo ambos os casos.
* [ ] Interface do adapter continua compatível (ou contrato atualizado/documentado).

---

### Tarefa C2 — Separar `personality` de `backstory` no modelo de suspeito - CONCLUÍDO

**Prioridade:** P1
**Tipo:** Modelo de conteúdo / qualidade narrativa
**Impacto:** Médio-Alto

### Contexto

O código usa `suspect.backstory` como `personality` para o dummy. O adapter espera rótulos como `agressivo`, `nervoso`, `arrogante`, mas `backstory` tende a ser texto descritivo longo. Resultado: o dummy cai quase sempre no fallback neutro.

### Objetivo

Criar campo explícito de personalidade do suspeito e usar esse campo para o comportamento do NPC.

### Escopo

* Adicionar `personality` ao schema de cenário (`SuspectConfig`)
* Persistir em `SuspectModel`
* Consumir em `chat_service` para `suspect_state`

### Fora de escopo

* Sistema de traços compostos
* Prompt engineering avançado por arquétipo

### Arquivos impactados

* `app/domain/schema_scenario.py`
* `app/infra/db_models.py`
* `app/services/scenario_loader.py`
* `app/services/chat_service.py`
* cenários JSON (`scenarios/*.json`)

### Subtarefas técnicas

1. Adicionar campo opcional `personality`.
2. Criar fallback compatível (se não existir, usar neutro).
3. Atualizar loader e seeds/cenários.
4. Atualizar dummy adapter docs para aceitar valores esperados.

### Melhores práticas

* Separar conteúdo de lore (`backstory`) de parâmetro de comportamento (`personality`).
* Manter retrocompatibilidade com cenários antigos (campo opcional).

### DoD

* [ ] Suspeitos podem ter `personality` explícita sem quebrar cenários antigos.
* [ ] Dummy adapter varia respostas conforme personalidade.
* [ ] Cenário piloto atualizado com exemplos de personalidade.
* [ ] Teste de loader + teste de resposta dummy por personalidade.

---

### Tarefa C3 — Corrigir duplicação da última mensagem do jogador no prompt do LLM - CONCLUÍDO

**Prioridade:** P1
**Tipo:** Bug de integração IA
**Impacto:** Médio

### Contexto

`build_npc_prompt()` adiciona:

* histórico (`chat_history[-10:]`) — que já inclui a última mensagem do jogador salva,
* e depois adiciona novamente `player_message`.

Isso duplica o último input, distorcendo resposta e tom do NPC.

### Objetivo

Garantir que o prompt contenha a última mensagem do jogador **uma única vez**.

### Escopo

* Corrigir montagem do prompt em `prompt_builder.py`
* Definir contrato explícito: `chat_history` inclui ou não a última mensagem

### Fora de escopo

* Redesenhar prompt completo
* Estratégia de memória longa

### Arquivos impactados

* `app/services/prompt_builder.py`
* `app/services/chat_service.py`
* testes de adapter/prompt (novos)

### Subtarefas técnicas

1. Decidir padrão:

   * A) `chat_history` já contém turno atual → não append `player_message`
   * B) `chat_history` só até turno anterior → append `player_message`
2. Documentar no código/interface.
3. Adicionar teste unitário no builder garantindo ausência de duplicação.

### Melhores práticas

* Contrato de função explícito > comportamento implícito.
* Testes unitários de prompt builder para regressão.

### DoD

* [ ] Última mensagem do jogador aparece uma vez no prompt final.
* [ ] Contrato de `build_npc_prompt()` documentado.
* [ ] Teste unitário de regressão criado.

---

### Tarefa C4 — Reduzir contexto oculto enviado ao LLM (preservar fairness do backend soberano) - CONCLUÍDO

**Prioridade:** P1
**Tipo:** Game design + segurança narrativa
**Impacto:** Alto (consistência)

### Contexto

O LLM recebe `true_timeline`, `lies`, `case_summary` e outros dados internos. Mesmo com instruções, isso aumenta risco de vazamento indireto (insinuações, confirmações involuntárias, informação além dos segredos revelados).

Se o princípio é “IA não decide e não revela fora do backend”, o ideal é minimizar o conhecimento oculto enviado.

### Objetivo

Enviar ao LLM apenas o contexto necessário para estilo/nuance, reduzindo risco de vazamento.

### Escopo (MVP)

* Criar modo “strict_npc_context”
* Remover do prompt (ou tornar opcional por config):

  * `true_timeline`
  * `lies` completos
  * `case_summary` sensível, se redundante
* Manter:

  * contexto público do caso
  * persona/estilo
  * segredos já revelados
  * pressão (evidências apresentadas)

### Fora de escopo

* Sistema de tool-calling para validação de resposta
* Pós-processamento semântico de respostas do LLM

### Arquivos impactados

* `app/services/npc_context_builder.py`
* `app/services/prompt_builder.py`
* `app/services/ai_adapter_openai.py`
* env/config (`NPC_AI_STRICT_MODE`, opcional)

### Subtarefas técnicas

1. Definir contrato mínimo de contexto para IA.
2. Implementar feature flag (opcional, recomendado para comparação).
3. Atualizar prompt com regras alinhadas ao novo contexto.
4. Criar testes unitários do builder validando ausência de campos sensíveis.

### Melhores práticas

* Princípio do menor privilégio aplicado à IA.
* Não confiar só em instrução textual para enforcement de regra.

### DoD

* [ ] `true_timeline` e `lies` podem ser omitidos do LLM via configuração padrão do MVP.
* [ ] Prompt continua funcionando com dummy e OpenAI.
* [ ] Teste valida que campos sensíveis não são enviados em modo estrito.
* [ ] README explica o modo estrito e o racional.

---

## EPIC D — Consistência de progressão (P1)

---

### Tarefa D1 — Corrigir semântica de `progress` e `is_closed` (incluindo caso sem core secrets)

**Prioridade:** P1
**Tipo:** Regra de estado / UX
**Impacto:** Médio-Alto

### Contexto

`apply_evidence_to_suspect()` calcula `progress` com base em segredos `is_core`. Se não houver segredos core:

* `progress = 1.0`
* mas `is_closed` não vira `True` (pela condição atual)

Isso gera estado inconsistente. Além disso, o fechamento automático pode ser agressivo para alguns cenários.

### Objetivo

Tornar `progress` e `is_closed` semanticamente consistentes e previsíveis.

### Escopo (MVP)

* Corrigir caso `total_core == 0`
* Documentar regra oficial:

  * se sem core secrets, qual o comportamento esperado?
* Recomendação MVP:

  * `progress = 1.0` e `is_closed = False` **com justificativa**, ou
  * `progress = 1.0` e `is_closed = True` (se “sem conteúdo extra”)

**Escolher uma regra e manter consistente.**

### Fora de escopo

* Novo modelo sofisticado de progressão por contradições
* Rebalanceamento narrativo de todos os cenários

### Arquivos impactados

* `app/services/secret_service.py`
* `app/services/session_service.py` (visões de estado)
* README (explicação de progresso)

### Subtarefas técnicas

1. Definir regra alvo.
2. Ajustar cálculo e fechamento.
3. Cobrir caso sem core secrets em teste.
4. Validar impacto em endpoints de status/overview.

### Melhores práticas

* Estados derivados devem ser semanticamente coerentes.
* Regra de negócio precisa estar documentada no código e README.

### DoD

* [ ] Caso sem core secrets tem comportamento definido e testado.
* [ ] `progress` e `is_closed` não entram em estado contraditório sem justificativa.
* [ ] Endpoints retornam estado consistente após confrontos.

---

### Tarefa D2 — Introduzir estado mínimo de “evidência efetiva” no retorno de turno (UX sem board visual)

**Prioridade:** P1
**Tipo:** UX backend / contrato de resposta
**Impacto:** Médio

### Contexto

O jogo já retorna `revealed_secrets`, mas não deixa explícito para a UI se a evidência foi efetiva naquele turno de forma simples e estável. Isso dificulta feedback claro ao jogador.

### Objetivo

Adicionar indicador mínimo no retorno do turno:

* `evidence_effect`: `"none" | "revealed_secret" | "duplicate"`

### Escopo

* Enriquecer resposta de `POST .../messages`
* Baseado no resultado da aplicação de evidência

### Fora de escopo

* Case board completo
* Sistema de dicas automáticas

### Arquivos impactados

* `app/api/sessions.py`
* serviço de turno (A1)
* `app/services/secret_service.py`

### Subtarefas técnicas

1. Definir enum/strings estáveis.
2. Determinar lógica:

   * sem `evidence_id` -> `"none"`
   * com `evidence_id` que revela algo novo -> `"revealed_secret"`
   * com `evidence_id` sem novo efeito mas já usado -> `"duplicate"` (ou `"none"`, se simplificar)
3. Atualizar contrato e docs.

### Melhores práticas

* Feedback de ação deve ser explícito e desacoplado da interpretação textual da IA.

### DoD

* [ ] Endpoint retorna `evidence_effect` consistente.
* [ ] UI pode depender do campo sem ler texto do NPC.
* [ ] Testes cobrem pelo menos 3 casos.

---

## EPIC E — Robustez do pipeline de cenários e manutenção (P1/P2)

---

### Tarefa E1 — Tornar `scenario_loader` transacional (all-or-nothing)

**Prioridade:** P1
**Tipo:** Pipeline de conteúdo / integridade de dados
**Impacto:** Alto para autoria e playtest

### Contexto

`load_scenario_from_json()` faz múltiplos `commit()` parciais. Se um erro ocorrer no meio (ex.: `culprit` inválido, secret referenciando evidência inexistente), parte do cenário pode ficar persistida. Isso polui a base e atrapalha testes.

### Objetivo

Garantir que o carregamento de um cenário seja atômico:

* sucesso completo ou rollback completo.

### Escopo

* Refatorar loader para usar uma transação única por cenário
* Fazer validações antes de commits sempre que possível

### Fora de escopo

* Alembic completo
* Versionamento formal de conteúdo por schema evolution

### Arquivos impactados

* `app/services/scenario_loader.py`
* `app/services/bootstrap_service.py` (efeito indireto)

### Subtarefas técnicas

1. Ler + validar JSON em memória.
2. Inserir cenário/suspeitos/evidências/segredos dentro de uma transação.
3. `commit()` apenas ao final.
4. Em erro, `rollback()` e log claro.
5. Criar teste com JSON inválido e confirmar base limpa.

### Melhores práticas

* Conteúdo é dado de produção do jogo; deve ter a mesma disciplina de transação.
* Validar referências cruzadas antes de persistência final.

### DoD

* [ ] Falha no loader não deixa registros parciais do cenário no DB.
* [ ] Loader continua idempotente para cenário já existente.
* [ ] Teste de rollback de cenário inválido implementado.

---

### Tarefa E2 — Limpar pontos de entrada inconsistentes (`start_app` inexistente) e padronizar execução

**Prioridade:** P2 (mas rápida e recomendada)
**Tipo:** Manutenção / developer experience
**Impacto:** Médio

### Contexto

`app/__init__.py` e `app/__main__.py` tentam importar `start_app` de `app.main`, mas `app.main` não define `start_app`. Isso cria ruído e confusão operacional.

### Objetivo

Padronizar entrypoints do projeto e remover código morto/inconsistente.

### Escopo

* Ajustar `__main__.py` e `__init__.py`
* Documentar forma oficial de execução (ex.: `uvicorn app.main:app --reload`)

### Fora de escopo

* CLI completa de administração
* Dockerização

### Arquivos impactados

* `app/__init__.py`
* `app/__main__.py`
* `README`

### Subtarefas técnicas

1. Remover referência a `start_app` inexistente.
2. Se quiser manter `python -m app`, implementar entrypoint válido com uvicorn.
3. Atualizar README com comando oficial.

### Melhores práticas

* Um único caminho oficial de execução reduz erros em onboarding.
* Remover código morto cedo.

### DoD

* [ ] `python -m app` funciona ou é removido/documentado corretamente.
* [ ] README contém instrução de execução válida.
* [ ] Não há import quebrado relacionado a `start_app`.

---

## EPIC F — Testes de regressão e documentação de contrato (P0/P1)

---

### Tarefa F1 — Criar suíte de testes de regressão do loop principal (anti-bypass + integridade)

**Prioridade:** P0
**Tipo:** Testes automatizados
**Impacto:** Crítico

### Contexto

O projeto já possui testes de happy path, mas a refatoração proposta altera regras sensíveis do loop. Sem testes de regressão específicos, existe alto risco de reintroduzir bypass e inconsistências.

### Objetivo

Cobrir com testes automatizados os comportamentos críticos definidos nesta refatoração.

### Escopo mínimo (MVP)

Criar testes para:

1. Não pode acusar com evidência nunca usada
2. Não pode jogar após sessão finalizada
3. Turno é atômico (rollback em falha)
4. Endpoint não expõe `is_mandatory`
5. Dummy não responde como incriminação quando evidência não teve efeito

### Fora de escopo

* Cobertura total de IA OpenAI real
* Testes E2E de frontend

### Arquivos impactados

* `tests/` (novos arquivos)
* fixtures / DB de teste
* possivelmente `DummyNpcAIAdapter` mock/stub

### Subtarefas técnicas

1. Criar fixtures para cenário e sessão.
2. Adicionar teste de API para contrato de `GET /sessions/{id}/evidences`.
3. Adicionar teste de acusação inválida por evidência não usada.
4. Adicionar teste de sessão finalizada.
5. Adicionar teste de rollback forçando exceção no adapter/serviço.

### Melhores práticas

* Testar regra de jogo na camada de API e na camada de serviço.
* Testes de regressão devem ser pequenos, determinísticos e rápidos.

### DoD

* [ ] 5 regressões críticas cobertas.
* [ ] Testes rodam com provider dummy sem depender de OpenAI.
* [ ] Testes falham no código antigo e passam no código refatorado (critério ideal).
* [ ] CI local (`pytest -q`) permanece rápida.

---

### Tarefa F2 — Atualizar README e contrato da API para refletir o MVP real após refatoração

**Prioridade:** P1
**Tipo:** Documentação técnica / produto
**Impacto:** Alto (alinhamento de equipe)

### Contexto

A documentação atual comunica corretamente alguns princípios, mas omite detalhes importantes de integridade (ex.: restrição de evidências usadas na acusação) e expõe uma expectativa de “interrogatório livre” maior do que a mecânica real.

Após a refatoração, a documentação precisa alinhar expectativa de gameplay e contrato da API.

### Objetivo

Atualizar documentação para refletir:

* regras reais do MVP
* endpoints e respostas atuais
* invariantes do backend soberano
* limitações conhecidas do MVP

### Escopo

* README
* exemplos de payload/resposta
* seção “regras do veredito”
* seção “limitações do MVP”
* instruções de execução/teste

### Fora de escopo

* Documentação de game design completa (GDD extenso)
* Docs de frontend

### Arquivos impactados

* `README.md`
* possivelmente `/docs` (se existir)

### Subtarefas técnicas

1. Remover referências a campos públicos de spoiler (`is_mandatory`).
2. Documentar regra “acusação só com evidências usadas/confirmadas”.
3. Documentar erro em sessão finalizada.
4. Documentar provider dummy vs OpenAI e limitações.
5. Atualizar fluxo rápido via API.

### Melhores práticas

* Documentação deve refletir comportamento observável, não intenção futura.
* Deixar limitações explícitas melhora playtest e priorização.

### DoD

* [ ] README compatível com comportamento real da API.
* [ ] Exemplos de resposta atualizados.
* [ ] Limitações do MVP explicitadas sem contradizer o sistema.
* [ ] Passos de setup/execução/testes validados.

---

# 4) Ordem recomendada de execução (sequência prática)

## Sprint 1 (P0) — preservar o core loop

1. **A1** Turno atômico
2. **A2** Bloqueio de sessão finalizada
3. **A3** Normalização de erros de domínio → HTTP
4. **B2** Validação de IDs da acusação
5. **B3** Exigir evidências usadas/confirmadas na acusação
6. **B1** Remover spoilers `is_mandatory`
7. **F1** Testes de regressão P0 (pode ser paralelo, mas idealmente acompanha cada item)

## Sprint 2 (P1) — consistência de feedback e narrativa

8. **B4** Registrar efetividade da evidência
9. **C1** Corrigir dummy (`revealed_now`)
10. **C3** Corrigir duplicação no prompt
11. **C2** Separar `personality` de `backstory`
12. **C4** Reduzir contexto oculto no LLM
13. **D1** Revisar `progress/is_closed`
14. **D2** `evidence_effect` no retorno do turno
15. **F2** Atualizar README/API docs

## Sprint 3 (P1/P2) — pipeline e manutenção

16. **E1** Loader transacional
17. **E2** Entrypoints/execução padronizados

---

# 5) Critérios globais de qualidade (aplicar em todas as tarefas)

## Padrões de implementação

* Serviços retornam apenas dados serializáveis (manter regra já adotada)
* Regras de negócio críticas na camada de serviço, não na API
* Commits DB centralizados em fluxos compostos
* Erros de domínio com mensagens claras e status HTTP consistente
* Testes de regressão para toda regra de gameplay alterada

## Critérios de aceite globais (DoD transversal)

* [ ] Nenhuma refatoração P0 permite bypass do loop por payload direto
* [ ] Nenhuma refatoração P0 introduz estado parcial de turno
* [ ] Todos os endpoints alterados têm testes de sucesso + erro
* [ ] README/API docs atualizados quando contrato público muda
* [ ] Provider dummy continua suficiente para testes automatizados

---

# 6) Backlog futuro (fora do escopo MVP, mas preparado pelas refatorações)

Estes itens não entram agora, mas as refatorações acima deixam base pronta:

* Estado explícito de contradições (`lie_exposures`)
* Score de eficiência investigativa (turnos, confrontos inúteis)
* “Case board” textual consolidado
* Epílogos ricos por resultado
* Regras de suspeito “pressionado” vs “fechado”
* Evidências com dependência/ordem narrativa

---

Se quiser, eu posso converter esse backlog em um **formato operacional para execução por agentes** (ex.: `Epic → Story → Task → Subtask → DoD → Test Cases`) em **Markdown separado por sprint**, pronto para colar em Jira/Notion/GitHub Projects.
