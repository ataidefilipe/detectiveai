📋 Backlog — Sala de Interrogatório (Ajustes Pós-MVP)
🔹 Prioridade P0 — Correções necessárias (baixo esforço, alto impacto)
TS-01 — Corrigir busca incorreta de cenário no fluxo de acusação

Descrição
Corrigir o erro lógico no endpoint /sessions/{id}/accuse, onde o sistema tenta buscar um cenário usando real_culprit_id em vez de scenario_id.

Tarefas

Remover a query incorreta de ScenarioModel

Ou substituir pela busca correta via session.scenario_id

Garantir que a resposta da acusação não dependa dessa query

Pronto quando

O endpoint /accuse não faz query usando real_culprit_id

O fluxo de acusação funciona corretamente para:

wrong

partial

correct

Todos os testes existentes continuam passando

TS-02 — Eliminar consulta redundante de estado do suspeito no overview

Descrição
Evitar chamadas duplicadas ao banco ao buscar progress e is_closed no endpoint de overview da sessão.

Tarefas

Ajustar get_session_overview para ser a fonte única de:

progress

is_closed

Remover a chamada extra a get_suspect_state no endpoint

Pronto quando

O endpoint GET /sessions/{id} retorna progresso e status completos

Nenhuma consulta adicional é feita por suspeito

A resposta da API permanece inalterada para o frontend

🔹 Prioridade P1 — Consistência de domínio (baixo risco)
TS-03 — Persistir final_phrase no modelo de suspeito

Descrição
Adicionar suporte real ao campo final_phrase, conforme descrito no README e usado no AI Adapter.

Tarefas

Adicionar final_phrase em:

SuspectModel

SuspectConfig (JSON do cenário)

Ajustar scenario_loader para persistir o campo

Usar final_phrase persistido no ai_adapter_dummy

Pronto quando

O JSON de cenário pode definir final_phrase

O banco persiste esse valor

O NPC usa a frase correta quando is_closed == True

Nenhum comportamento existente é quebrado

TS-04 — Definir fonte única de cálculo de progresso do suspeito

Descrição
Evitar duplicação de lógica de progresso entre serviços.

Tarefas

Definir secret_service como responsável único pelo cálculo

Marcar calculate_suspect_progress como helper (ou removê-lo)

Garantir que progress seja sempre atualizado após aplicação de evidência

Pronto quando

O progresso é calculado em apenas um local

Não há duplicação de regra

Testes continuam passando sem alteração

🔹 Prioridade P2 — Higiene de código (opcional, rápido)
TS-05 — Remover arquivo de endpoint não utilizado

Descrição
Eliminar arquivos não utilizados para reduzir ruído cognitivo.

Tarefas

Remover app/api/chat_endpoints.py

Garantir que não há imports quebrados

Pronto quando

O arquivo não existe mais

A aplicação inicia normalmente

Nenhum endpoint deixa de funcionar

TS-06 — Padronizar retorno dos serviços para uso em API

Descrição
Melhorar previsibilidade dos serviços, sem refatoração pesada.

Tarefas

Padronizar retornos de serviços para:

dict no boundary da API

Garantir que ORM não “vaze” para o controller

Pronto quando

Todos os endpoints retornam dados serializáveis

Não há DetachedInstanceError

O padrão é documentado (comentário ou README técnico)

🔹 Prioridade P3 — Qualidade de entendimento (documentação)
TS-07 — Ajustar descrição de IA no README

Descrição
Deixar explícito que a IA não interfere na lógica do jogo.

Tarefas

Alterar o trecho:

“IA improvisa estilo e nuance”

Para:

“IA afeta apenas forma, não regra nem verdade”

Pronto quando

O README reflete corretamente o papel da IA

Nenhuma expectativa errada é criada para futuros contribuidores

🧭 Visão resumida (ordem sugerida de execução)

TS-01 — bug real

TS-02 — performance/clareza

TS-03 — alinhamento com README

TS-04 — consistência de regra

TS-05 — limpeza rápida

TS-06 — padronização leve

TS-07 — ajuste conceitual