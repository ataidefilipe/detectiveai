Avaliando **o que já existe** vs. o que um **jogador precisa para experimentar o loop completo e dar feedback**, seu backend está bem encaminhado — o que falta está mais em **“camada de experiência”** (UI/fluxo) e **alguns endpoints de apoio** pra não depender de estado no client.

## 1) Fluxo do jogo hoje (com o que você já tem)

### Entrada

* ✅ `GET /scenarios` (lista)
* ✅ `GET /scenarios/{id}` (detalhe com suspeitos/evidências e marca obrigatórias)

### Início

* ✅ `POST /sessions` (cria sessão)
* ✅ bootstrap de DB + load de cenário JSON no startup

### Interrogatório

* ✅ `GET /sessions/{id}/suspects` (traz backstory + initial_statement + progress/is_closed)
* ✅ `GET /sessions/{id}/evidences` (lista evidências + obrigatórias)
* ✅ `POST /sessions/{id}/suspects/{suspect_id}/messages` (turno completo: player msg, aplica evidência, NPC reply, retorna `revealed_secrets` + `suspect_state`)
* ✅ `GET /sessions/{id}/suspects/{suspect_id}/messages` (histórico)
* ✅ `GET /sessions/{id}/suspects/{suspect_id}/status` (progress/is_closed)

### Final

* ✅ `POST /sessions/{id}/accuse` (wrong/partial/correct + metadados)

---

## 2) O que está faltando para o MVP “jogável” (sem overengineering)

### Falta 1 — Uma UI mínima (ou “cliente de jogo”)

Hoje, o jogador só “joga” via Postman/curl. Pra **feedback real**, precisa de um front simples (pode ser feio, mas funcional).

### Falta 2 — Recuperar “segredos revelados” após refresh

No turno, você retorna `revealed_secrets`. Mas se o jogador recarregar a página ou entrar depois, não existe endpoint que retorne **o estado completo do suspeito** com:

* segredos já revelados (conteúdo)
* progresso / fechado

Sem isso, a UX quebra fácil.

### Falta 3 — Exportar sessão para feedback

Você já persiste tudo (mensagens, uso de evidências, veredito). Falta uma forma fácil de “**me manda o caso que você jogou**”:

* um endpoint de export (JSON) resolve 80% do feedback qualitativo.

### Falta 4 — Pequenas regras de “fluxo” para não virar bagunça

Sem segurança/overengineering, ainda vale ter 2 guardas simples:

* não permitir mandar mensagem se `session.status == finished`
* não permitir acusar duas vezes

Isso evita feedback “ruim” por bug/uso indevido.

---

# 3) Backlog detalhado (MVP para jogador testar)

Abaixo, backlog **priorizado** (P0 = necessário pra alguém jogar e opinar; P1 = aumenta qualidade do feedback; P2 = pós-playtest).
Cada item com **Descrição**, **Boas práticas**, **Definition of Done (DoD)**.

---

## ÉPICO A — “Jogo jogável” (P0)

### US-A01 (P0) — Criar UI mínima para jogar (web simples)

**Descrição:** Como jogador, quero jogar no navegador: escolher cenário, iniciar sessão, conversar com suspeitos, usar evidências e acusar.
**Sugestão MVP:** SPA simples (HTML + JS + fetch) ou React/Vite (se já curte). Sem login, sem build complexo.

**Escopo mínimo da UI:**

* Tela 1: lista cenários → “Iniciar”
* Tela 2: suspeitos + evidências + chat
* Dropdown de evidência (opcional) ao enviar mensagem
* Aba/área de “Acusar”: escolher suspeito + marcar evidências e enviar
* Tela/Modal de resultado (wrong/partial/correct)

**Boas práticas (MVP-friendly):**

* manter estado da sessão no client (session_id)
* chamar `GET chat_history` ao abrir suspeito
* exibir `revealed_secrets` do turno + “progresso”

**DoD:**

* consigo jogar o loop completo sem Postman
* funciona do zero: `uvicorn ...` + abrir UI e jogar
* README tem “Como rodar” (2–4 comandos)
* pelo menos 1 fluxo “happy path” validado manualmente

---

### US-A02 (P0) — Habilitar CORS aberto (para UI local)

**Descrição:** Como dev, preciso que a UI local consiga chamar a API.
**DoD:**

* CORS liberado para `http://localhost:*` (MVP)
* UI consegue chamar endpoints sem erro de CORS

---

### US-A03 (P0) — Endpoint de estado completo do suspeito na sessão (inclui segredos)

**Descrição:** Como jogador, quero ver os segredos já revelados de um suspeito mesmo após recarregar a página.

**Sugestão:** criar:

* `GET /sessions/{session_id}/suspects/{suspect_id}/state`
  retornando:

```json
{
  "suspect_id": 1,
  "progress": 0.5,
  "is_closed": false,
  "revealed_secrets": [{ "secret_id": 10, "content": "...", "is_core": true }]
}
```

**Boas práticas:**

* montar via `SessionSuspectStateModel.revealed_secret_ids` + query em `SecretModel`
* não vazar nada não-revelado

**DoD:**

* endpoint retorna segredos revelados corretamente
* funciona após restart/refresh
* teste automatizado cobrindo: “revela segredo → endpoint lista segredo”

---

### US-A04 (P0) — Travar ações inválidas por status da sessão

**Descrição:** Como jogador, não quero “quebrar” o jogo mandando mensagens depois de finalizar.

**Regras MVP:**

* se `session.status == finished`, bloquear:

  * `POST /messages`
  * `POST /accuse` (se já finalizada)

**DoD:**

* mensagens após finalização retornam 400/409 com mensagem clara
* acusação dupla retorna erro claro
* testes automatizados para ambos

---

## ÉPICO B — “Feedback e observabilidade simples” (P1)

### US-B01 (P1) — Exportar sessão completa em JSON

**Descrição:** Como dev, quero um endpoint que me permita analisar a experiência do jogador (pra debug e feedback).

**Sugestão:**

* `GET /sessions/{session_id}/export`
  Retorna:
* session (status, escolhido, resultado)
* scenario (título)
* suspeitos + estado
* chat_messages (ordenadas)
* evidence_usages
* required_evidence_ids

**Boas práticas:**

* retorno serializável
* ordenação do chat por timestamp

**DoD:**

* endpoint existe e retorna dados completos e coerentes
* consigo copiar JSON e analisar replay
* teste automatizado: cria sessão → faz 1 mensagem → acusa → export contém tudo

---

### US-B02 (P1) — “Script de playtest” (seed + quickstart)

**Descrição:** Como pessoa que vai testar, quero rodar e jogar em 2 minutos.

**Conteúdo:**

* `cp .env.example .env`
* `python init_db.py` (ou bootstrap)
* `uvicorn app.main:app --reload`
* abrir UI

**DoD:**

* README com “Quickstart”
* `.env.example` com `NPC_AI_PROVIDER=dummy` como padrão
* “como usar OpenAI” em seção separada (opcional)

---

## ÉPICO C — “Conteúdo para teste” (P1/P0 dependendo do seu cenário)

### US-C01 (P0/P1) — Revisar `scenarios/piloto.json` para playtest de verdade

**Descrição:** Um cenário piloto precisa ser bom o suficiente para o jogador entender o jogo e dar feedback sobre a experiência.

**Checklist mínimo de conteúdo:**

* 3–5 suspeitos com *vibe* diferente
* 6–10 evidências
* 1 culpado definido
* 2–4 evidências obrigatórias (não muitas)
* segredos “core” que realmente progridem
* mentiras com `broken_by` coerente (se estiver usando)

**DoD:**

* dá pra chegar em `partial` e `correct` com escolhas diferentes
* pelo menos 1 caminho de “evidência errada” gera fricção narrativa
* cenário carregando via bootstrap sem erro

---

## ÉPICO D — “Polimento mínimo de UX de API” (P2, mas barato)

### US-D01 (P2) — Mensagens de erro padronizadas e úteis

**Descrição:** Quando o jogador usar evidência inválida, suspeito errado etc., o erro deve ser legível (pra não virar feedback “quebrou”).

**DoD:**

* erros comuns retornam `detail` claro
* UI mostra a mensagem sem stacktrace

---

### US-D02 (P2) — “Guia do jogador” dentro da UI

**Descrição:** Uma caixinha “Como jogar” no topo para o playtest não travar.

**DoD:**

* texto curto (5–8 linhas) explicando evidência e acusação
* sem tutorial longo

---

# 4) Ordem recomendada (pra você ter playtest rápido)

**Sprint 1 (MVP jogável):**

1. US-A02 CORS
2. US-A03 Estado do suspeito com segredos
3. US-A04 Travar ações inválidas
4. US-A01 UI mínima

**Sprint 2 (feedback bom):**
5) US-B01 Export de sessão
6) US-B02 Quickstart
7) US-C01 Ajuste do cenário piloto

---
