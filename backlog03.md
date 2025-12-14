## Para um MVP “jogável”, o que está pendente?

### 1) O jogador já tem acesso a TODAS as informações que precisa?

Hoje ele tem:

* ✅ resumo do cenário (via `GET /sessions/{id}`: title/description)
* ✅ evidências (via `GET /sessions/{id}/evidences`)
* ✅ chat com NPCs (send + history)
* ✅ acusação final (via `/accuse`)

**Mas falta algo importante para a experiência mínima:**

* ⚠️ **Fichas dos suspeitos** completas: no overview você retorna `name/progress/is_closed`, mas não retorna **backstory** (e nem `final_phrase`, se a UI precisar).
* ⚠️ **Lista de cenários** (ou um jeito simples de saber `scenario_id` sem “chutar 1”).
* ⚠️ Fluxo de “bootstrap”: hoje você precisa rodar scripts (`init_db.py` + `load.py`) antes de subir a API. Para MVP jogável, o ideal é **subir e jogar**.

**Conclusão:** está *quase* jogável via API/Swagger, mas falta “colar” o início (cenários) e expor as fichas.

---

### 2) O NPC já tem IA? (real)

Hoje: **não** (é dummy). Para MVP, isso pode ser aceitável por 2 motivos:

* valida fluxo inteiro
* te dá testes determinísticos

Mas se a proposta do jogo é “interrogatório com IA generativa”, então para “MVP jogável” o mínimo é:

* plugar um **adapter OpenAI** simples
* com um **prompt rígido** que impeça inventar fatos (história fixa)

---

## Como deve ser o prompt do NPC (sem overengineering)

Objetivo: a LLM improvisa **estilo**, mas **não inventa** evidências/segredos.

### Contexto mínimo que você deve passar para a IA

* Cenário: `title`, `description`
* Suspeito: `name`, `backstory`, `final_phrase`, `is_closed`
* Chat history (últimas N mensagens)
* Evidência usada no turno (se houver): `evidence_id` + `name/description`
* Segredos já revelados (apenas os revelados)
* (Opcional) “regras do jogo” em texto claro

### Regras de prompt (o que não pode faltar)

* **Não inventar evidência, nomes, segredos ou eventos fora do contexto**
* Se `is_closed == True` → responder **somente** `final_phrase`
* Se evidência foi apresentada e **nenhum segredo foi revelado pelo backend**:

  * o NPC pode negar/desviar, mas **não pode “revelar” nada novo**
* Se evidência revelou segredos:

  * ele pode reagir e “admitir” **somente** o conteúdo revelado

> Importante: quem decide “o que foi revelado” é o **backend** (seu `secret_service`), não a IA.

### Integração (forma mais simples)

* Criar `OpenAINpcAIAdapter` que recebe os mesmos 3 inputs do adapter dummy:

  * `suspect_state`
  * `chat_history`
  * `player_message`
* Montar um prompt “system + user” e chamar a API
* Manter dummy como padrão em testes (env var troca provider)

---

# Backlog pro MVP jogável (com Definition of Done)

Vou organizar por prioridade real de “jogar do zero”.

## P0 — Necessário para jogar do início ao fim

### US-01 — Bootstrap automático do jogo ao subir a API - ok

**Por quê:** hoje precisa rodar scripts manualmente antes.
**Tarefas**

* Adicionar evento de startup no FastAPI:

  * `init_db()`
  * carregar `scenarios/*.json` se não existir cenário no banco
* Garantir que o loader não duplica (você já tem check por title)
  **Pronto quando**
* Rodar `uvicorn app.main:app` e conseguir:

  * criar sessão sem executar `init_db.py`/`load.py`
* Reiniciar servidor não duplica cenários

---

### US-02 — Listar cenários disponíveis - ok

**Por quê:** jogador/cliente precisa escolher cenário sem “adivinhar id=1”.
**Tarefas**

* Criar `GET /scenarios` retornando: `id`, `title`, `description`
* (Opcional) `GET /scenarios/{id}` com detalhes
  **Pronto quando**
* Um cliente consegue descobrir `scenario_id` via API
* Resposta é serializável e pequena

---

### US-03 — Expor fichas dos suspeitos (para UI/jogador)

**Por quê:** README diz que o jogador “conhece suspeitos”; hoje ele só vê nome/progresso.
**Tarefas**

* Criar `GET /sessions/{id}/suspects` (ou enriquecer overview) com:

  * `suspect_id`, `name`, `backstory`, `progress`, `is_closed`
* Garantir que não expõe segredos (somente ficha)
  **Pronto quando**
* O jogador consegue ver as fichas dos suspeitos sem acessar o banco
* A resposta não inclui segredos

---

### TS-07 — Adapter OpenAI (IA real) + fallback para Dummy (sem quebrar testes)

**Tarefas**

* Implementar `OpenAINpcAIAdapter` (novo arquivo)
* Configurar por env var: `NPC_AI_PROVIDER=dummy|openai`
* Criar `prompt_builder` simples e controlado (system + user)
* No `chat_service`, escolher adapter no startup (ou lazy init)
  **Pronto quando**
* Com `NPC_AI_PROVIDER=dummy` → tudo funciona como hoje (testes ok)
* Com `NPC_AI_PROVIDER=openai` + `OPENAI_API_KEY` → NPC responde via LLM
* IA **não revela** segredos fora do que o backend marcou como revelado

---

## P1 — Melhorias pequenas que deixam “jogar” agradável (sem inflar)

### US-04 — Melhorar resposta do endpoint de mensagem (turno) para UX

**Por quê:** a UI costuma precisar de mais contexto em 1 chamada.
**Tarefas**

* No retorno de `POST /messages`, incluir (sem duplicar demais):

  * `npc_message`
  * `revealed_secrets`
  * `suspect_state` resumido (progress/is_closed)
    **Pronto quando**
* UI consegue atualizar tela do suspeito sem fazer 2-3 chamadas adicionais

---

### TS-08 — Limitar histórico no prompt (controle de custo e coerência)

**Tarefas**

* Ao montar prompt: enviar apenas últimas N mensagens (ex.: 12)
* Incluir resumo curto opcional (sem overengineering: apenas concat)
  **Pronto quando**
* Prompt não cresce indefinidamente
* Respostas permanecem coerentes com o contexto

---

### TS-09 — Mini documentação “Como jogar via Swagger”

**Tarefas**

* Adicionar no README:

  * passo a passo do fluxo (criar sessão, listar evidências/suspeitos, chat, acusar)
  * exemplo de payloads
  * env vars para IA
    **Pronto quando**
* Um dev consegue rodar e jogar lendo só o README, sem te perguntar nada

---

## P2 — “Nice to have” (segura pra depois)

### US-05 — Depoimento inicial por suspeito (opcional)

**Por quê:** dá clima e direciona perguntas.
**Tarefas**

* Adicionar campo opcional `initial_statement` no JSON + DB
* Expor na ficha do suspeito
  **Pronto quando**
* Cada suspeito pode ter um “texto inicial” visível ao jogador

---

# O que eu faria primeiro (sequência recomendada)

1. **US-01 Bootstrap** (sem isso você sempre sofre pra testar)
2. **US-02 Listar cenários**
3. **US-03 Fichas de suspeitos**
4. **TS-07 OpenAI adapter + prompt controlado**
5. **TS-09 doc de jogo via swagger**

Isso te dá “MVP jogável” de verdade: **rodou, escolheu cenário, viu evidências/suspeitos, interrogou, acusou**.

Se você quiser, eu já escrevo o código da **US-01 + US-02 + US-03** (arquivos e trechos exatos) no mesmo estilo que fizemos nas TS anteriores, mantendo tudo simples e sem refatoração grande.
