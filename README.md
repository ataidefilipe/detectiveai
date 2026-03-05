# 🕵️ Sala de Interrogatório — MVP

> **Nome de trabalho:** Sala de Interrogatório
> **Status:** MVP funcional (backend completo + testes automatizados)
> **Stack:** Python · FastAPI · SQLAlchemy · SQLite · OpenAI (opcional)

---

## 1. Visão geral

**Sala de Interrogatório** é um jogo narrativo investigativo baseado em lógica, diálogo e evidências.

O jogador resolve um caso criminal por meio de **interrogatórios em chat** com NPCs suspeitos, utilizando evidências para pressionar, confrontar contradições e revelar informações relevantes.

🔑 **Princípio central do projeto**

> A **história é fixa**, existe **um culpado único por cenário**,
> e a **IA nunca decide o que é revelado** —
> ela apenas interpreta e responde **dentro dos limites definidos pelo backend**.

A IA é usada para **estilo, nuance e tensão dramática**, não para lógica de jogo. O backend é o guardião soberano das regras vitais (não repassamos a Timeline Oficial aos robôs para evitar falhas de spoiler!).

---

## 2. Loop básico de jogo

1. Jogador escolhe um **cenário**.
2. Lê a introdução do caso e conhece os suspeitos.
3. Visualiza a lista de **evidências disponíveis**.
4. Inicia interrogatórios em chat com os suspeitos em sessões de turnos *atômicos*.
5. Envia mensagens livres ou **confronta usando uma evidência id**.
6. Evidências corretas podem revelar **segredos** controlados matematicamente.
7. Quando se sentir pronto, o jogador faz uma **acusação final**:
   * escolhe o suspeito culpado
   * escolhe a **motivação** (o porquê o suspeito cometeu o crime) baseando-se nas opções do cenário `motive_options`
   * seleciona as evidências (Que **obrigatoriamente** o jogador precisa já ter apresentado em alguma conversa anterior — Evidências não engatilhadas resultarão em erro HTTP `409 Conflict`)
8. O sistema avalia o resultado e retorna `correct`, `partial` (ex: errou a motivação ou esqueceu evidência) ou `wrong`. A Sessão é formalmente *bloqueada e encerrada*.

---

## 3. Escopo do MVP

### Incluído no MVP

* 1 cenário piloto carregado via JSON Transactional.
* 3–5 suspeitos por cenário, cada um com `personality`, `final_phrase` e `mentiras modeladas`.
* Sessões de jogo persistidas em banco de SQLite (turnos isolados contra corrupção).
* API imutável sem *spoilers* ao Frontend (o game design não avisa em via pública quem tem as pistas obrigatórias).
* 2 Drivers de LLM (Dummy IA determinística para Debug e Adaptador OpenAI oficial).

### Fora do MVP (mas considerado no design)

* Multiplayer / Interface Visual em Unity.
* Autenticação / Rate limit
* Sistema dinâmico de descoberta de evidências na cena do crime (Point and Click)

---

## 4. Decisões de design consolidadas

### Evidências e Efeitividade
* O frontend não depende de referências hardcoded de banco. Existe endpoint `/evidences` e as chaves `is_mandatory` (vital pra resolver o caso) são ocultas em produção.
* A API esconde sistematicamente o preenchimento de `internal_note` no JSON de Scenarios, protegendo o jogador contra spoilers e reservando anotações para game designers do conteúdo.
* No retorno do Turno, avaliamos o `evidence_effect` (o impacto que a fala gerou sobre o NPC), retornando se o usuário acabou de *revelar um novo segredo*, usar algo *duplicado* ou algo sem efeito (*none*). 

### IA e Limits
* `DummyNpcAIAdapter` (determinístico, não cobra chaves de API). O Dummy apenas elogia ou ofende o Detetive baseado se a métrica `evidence_effect` bateu nos calos dele ou não.
* `OpenAINpcAIAdapter` (Chat IA realista). O adaptador é submetido ao "Modo Estrito": Ocultamos deliberadamente as variáveis `true_timeline` e as `lies` da System Message injetada para a IA, obrigando as IAs modernas a inventarem desculpinhas ou calarem a boca pro detetive em vez de soltar o assassino cedo demais.

---

## 5. Novidades Recentes (Épicos A-H)

O motor de jogo foi drasticamente expandido para suportar conversas mais imersivas e regras avançadas:

* **NLP e Transições de Estado (Episódios A e B):** A análise de mensagens e a resolução de turnos foram separadas da geração de texto da IA. O backend agora rastreia o estado conversacional de cada suspeito (postura, paciência, pressão e rapport). A agressividade ou repetição do detetive afeta ativamente a tolerância do NPC.
* **Tópicos e Sensibilidade (Episódio C):** O interrogatório possui uma árvore de tópicos do cenário. Tocar em tópicos sensíveis causa reações sistêmicas no suspeito.
* **Política de Conhecimento Segregada (Episódios D e E):** O backend adota o conceito de "O que o NPC está autorizado a dizer agora". Segredos ligados a evidências (*Secrets*) e fofocas/contextos de história (*Knowledge Items*) são liberados em camadas pela `reveal_policy`. As evidências podem falhar silenciosamente se o assunto estiver fora de contexto (`out_of_context`).
* **Segurança de LLM (Episódio F):** Prompts orientados a "Modos de Resposta" rígidos (evasivo, recusa, final). Adicionado um Fallback determinístico caso a API da LLM caia em produção.
* **Feedback Sistêmico (Episódio G e H):** A API agora responde dicas visuais em tempo real (`npc_shift`, `topic_signal` e `conversation_effect`), guiando sutilmente o frontend. Exceções e erros são altamente tipados (DomainError e NotFoundError) blindando o backend.
* **Ciclo Narrativo Avançado (Sprints 2 e 3):** 
   - A Acusação Final agora pesa o _Motivo_. 
   - O Bootstrapping de Scenarios é __Idempotente__ (via `scenario_code`), permitindo atualizar cenários on-the-fly sem dropar o DB.
   - Thresholds de pressão e reações numéricas externalizadas num contêiner `app.core.config.Settings` fixo.
   - Trillha de observabilidade estruturada (`telemetry_logger`) no terminal.

---

## 6. Como Executar

### 1. Iniciar Aplicação Local (Uvicorn Native)

Instale os resquisitos (via Poetry ou Pip) e suba o backend FastAPI usando o Entrypoint oficial do módulo:

```bash
python -m app
```
A Engine rodará por padrão travada na porta `localhost:8000` suportando recarregamentos dinâmicos (*hot reload*).

### 2. Rodar a Suíte Anti-Cheat e Regressão

O projeto possuí cerca de 13 Invariantes Críticos que protegem a sessão desde turnos zumbis à corrupção transacional de banco.
```bash
pytest tests
```

---

## 6. Fluxo rápido via API

1. `POST /sessions` (Body: `{ "scenario_id": 1 }`)
2. `GET /sessions/{id}/evidences` (Retorna Pistas sem Spoilers)
3. `POST /sessions/{id}/suspects/{id}/messages` 
> Body de Exemplo (Turno):
```json
{
  "text": "Explique esta pegada no chão!",
  "evidence_id": 3
}
```
> Resposta Base:
```json
{
  "player_message": { ... },
  "npc_message": { ... },
  "revealed_secrets": [],
  "evidence_effect": "out_of_context",
  "system_feedback": {
    "conversation_effect": "neutral",
    "npc_shift": "none",
    "topic_signal": "weak",
    "feedback_hints": ["Ele parece se incomodar com esse tópico, continue pressionando."]
  },
  "suspect_state": {
    "progress": 0.5,
    "is_closed": false
  }
}
```
133. `POST /sessions/{id}/accuse` 
> Body de Exemplo:
```json
{
  "suspect_id": 1,
  "motive_key": "financial_gain",
  "evidence_ids": [1, 2]
}
```
> Se tentada após já finalizada ou acusando com Evidências Id nunca levadas à interrogatório, o Backend bloqueará como `409 Conflict`.