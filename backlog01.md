Vou assumir:

* Python 3.x
* Backend com **FastAPI + SQLite + SQLAlchemy** (ou similar)
* Cenário carregado de **JSON** (pra já preparar o futuro “cenários da comunidade”)

---

## Fase 01 – Backlog focado em desenvolvimento

### Bloco 0 – Setup de projeto

**T1 – Criar estrutura base do projeto Python** - ok

* Criar repositório/projeto com estrutura mínima, ex.:
  `app/` (código), `tests/`, `app/api/`, `app/domain/`, `app/services/`, `app/infra/`.
* Configurar `pyproject.toml` ou `requirements.txt`.
  ✅ *Pronto quando:* o projeto instala e roda `python -m app` (ou comando similar) sem erro.

---

**T2 – Adicionar dependências principais** - ok

* Incluir e instalar:

  * `fastapi`
  * `uvicorn`
  * `sqlalchemy`
  * `pydantic`
  * `alembic` (opcional, se quiser migração) ou pelo menos `sqlalchemy[asyncio]`/`sqlite`.
    ✅ *Pronto quando:* `pip install -r requirements.txt` funciona e `import fastapi`/`import sqlalchemy` rodam sem erro.

---

**T3 – Criar servidor FastAPI básico (hello world)** - ok

* Criar `app/main.py` com instância FastAPI.
* Adicionar rota `GET /health` retornando `{status: "ok"}`.
* Adicionar comando de execução (`uvicorn app.main:app --reload`).
  ✅ *Pronto quando:* acessar `/health` no browser ou curl retorna `{"status":"ok"}`.

---

### Bloco 1 – Modelo de domínio (Python / ORM)

**T4 – Definir modelos Pydantic para entidades principais** - ok

* Criar `app/domain/models.py` com Pydantic models para:

  * `Scenario`, `Suspect`, `Evidence`, `Secret`, `Session`, `SessionSuspectState`, `NpcChatMessage`, `SessionEvidenceUsage`.
* Modelos focados em validação/entrada/saída de API (não precisam ter todos os campos do banco ainda, só o essencial).
  ✅ *Pronto quando:* os modelos são importáveis e têm tipos/atributos coerentes com o que definimos conceitualmente.

---

**T5 – Criar modelos ORM (SQLAlchemy) para armazenamento** - ok

* Em `app/infra/db_models.py`, criar classes SQLAlchemy para:

  * `ScenarioModel`
  * `SuspectModel`
  * `EvidenceModel`
  * `SecretModel`
  * `SessionModel`
  * `SessionSuspectStateModel`
  * `NpcChatMessageModel`
  * `SessionEvidenceUsageModel`
* Relacionar corretamente (FK de `scenario_id`, `suspect_id`, etc.).
  ✅ *Pronto quando:* `Base.metadata.create_all(engine)` roda sem erro e as tabelas são criadas.

---

**T6 – Configurar conexão SQLite e inicialização do banco**

* Criar `app/infra/db.py` com:

  * Função para criar engine SQLite (ex.: `sqlite:///./game.db`).
  * SessionLocal (SQLAlchemy).
  * Função `init_db()` que chama `create_all` (ou migração inicial).
    ✅ *Pronto quando:* rodar um script `init_db.py` gera o arquivo `game.db` com as tabelas.

---

### Bloco 2 – Carregamento de cenário (JSON → banco)

**T7 – Definir esquema de JSON para cenário**

* Em `app/domain/schema_scenario.py`, definir classes Pydantic para o JSON do cenário:

  * `ScenarioConfig`, `SuspectConfig`, `EvidenceConfig`, `SecretConfig`, etc.
* Esse JSON terá tudo que é “fixo”: culpado, segredos, evidências, cronologia.
  ✅ *Pronto quando:* um JSON de exemplo valida corretamente com essas classes.

---

**T8 – Implementar loader de cenário a partir de JSON**

* Criar `app/services/scenario_loader.py` com função:

  * `load_scenario_from_json(path: str) -> ScenarioModel`
* Ler o arquivo JSON, validar com Pydantic, popular as tabelas `Scenario`, `Suspect`, `Evidence`, `Secret`.
* Evitar duplicar se já existir (pelo menos via título ou id interno).
  ✅ *Pronto quando:* rodar o loader insere um cenário completo no banco sem erro.

---

**T9 – Criar arquivo JSON de cenário piloto mínimo**

* Criar `scenarios/piloto.json` com:

  * 1 cenário
  * 3–4 suspeitos
  * 5–8 evidências
  * Segredos mapeando evidência → segredo do suspeito
  * Culpado definido
    ✅ *Pronto quando:* `load_scenario_from_json("scenarios/piloto.json")` roda com sucesso e dados aparecem nas tabelas.

---

### Bloco 3 – Sessão de jogo e estados

**T10 – Serviço para criar sessão de jogo**

* Em `app/services/session_service.py`, criar função:

  * `create_session(scenario_id: int) -> SessionModel`
* Inicializar:

  * `SessionModel(status="in_progress")`
  * Criar registros `SessionSuspectState` para cada suspeito do cenário (sem segredos revelados).
    ✅ *Pronto quando:* chamar `create_session` cria uma sessão nova no banco e estados iniciais por suspeito.

---

**T11 – API: endpoint para criar sessão (POST /sessions)**

* Criar rota `POST /sessions` recebendo `scenario_id`.
* Chamar `create_session` e retornar `session_id` + info básica.
  ✅ *Pronto quando:* `POST /sessions` retorna um ID de sessão válido e a sessão está no banco.

---

**T12 – Serviço para consultar estado resumido da sessão**

* Função `get_session_overview(session_id)` que retorna:

  * dados da sessão
  * lista de suspeitos com progresso (placeholder 0% por enquanto)
  * cenário básico (título, objetivo).
    ✅ *Pronto quando:* chamada retorna objeto Python com essas informações montadas de forma consistente.

---

**T13 – API: endpoint GET /sessions/{session_id}**

* Expor `get_session_overview` na API.
  ✅ *Pronto quando:* `GET /sessions/{id}` retorna JSON legível com status, cenário e lista de suspeitos.

---

### Bloco 4 – Chat com NPC e uso de evidência

**T14 – Serviço para registrar mensagem do jogador**

* Em `app/services/chat_service.py`, criar função:

  * `add_player_message(session_id, suspect_id, text, evidence_id=None)`
* Registrar em `NpcChatMessage` com `sender_type="player"`.
* Se `evidence_id` não for `None`, também registrar em `SessionEvidenceUsage`.
  ✅ *Pronto quando:* função cria registros corretos nas tabelas e pode ser chamada em sequência.

---

**T15 – Serviço para aplicar evidência sobre segredos do suspeito**

* Ainda em `chat_service` ou `secret_service`, criar função:

  * `apply_evidence_to_suspect(session_id, suspect_id, evidence_id) -> list[SecretModelRevelado]`
* Lógica:

  * Buscar segredos do suspeito que têm `evidence_id` correspondente.
  * Marcar esses segredos como revelados na `SessionSuspectState` (ex: guardar lista de `secret_ids` revelados).
    ✅ *Pronto quando:* dado um par (suspeito, evidência), os segredos relevantes são marcados como revelados na sessão.

---

**T16 – Definir interface para adaptador de IA (sem implementação real ainda)**

* Em `app/services/ai_adapter.py`, criar interface/abstração:

  * `class NpcAIAdapter:` com método `generate_reply(suspect_state, chat_history, player_message) -> str`.
* Por enquanto, sem chamar API externa; só assinatura e docstring.
  ✅ *Pronto quando:* a interface pode ser importada e usada por outros serviços.

---

**T17 – Criar implementação dummy do adaptador de IA**

* `DummyNpcAIAdapter(NpcAIAdapter)` que:

  * Usa dados do suspeito e dos segredos revelados para montar uma resposta determinística (por exemplo, concatenando frases pré-definidas).
  * Não precisa ser inteligente; serve pra testar fluxo.
    ✅ *Pronto quando:* `generate_reply` retorna uma string coerente sem precisar de conexão externa.

---

**T18 – Serviço para gerar resposta do NPC**

* Criar função:

  * `add_npc_reply(session_id, suspect_id, player_message_id) -> NpcChatMessageModel`
* Responsabilidades:

  * Buscar histórico recente de mensagens da sessão/suspeito.
  * Montar `suspect_state` (incluindo segredos já revelados).
  * Chamar `NpcAIAdapter.generate_reply(...)`.
  * Salvar resposta do NPC em `NpcChatMessage` (`sender_type="npc"`).
    ✅ *Pronto quando:* chamada gera e persiste uma mensagem de NPC ligada ao player_message.

---

**T19 – API: endpoint POST /sessions/{session_id}/suspects/{suspect_id}/messages**

* Corpo da requisição: `{ "text": "...", "evidence_id": null | int }`.
* Fluxo:

  * Chamar `add_player_message`.
  * Se `evidence_id` presente: chamar `apply_evidence_to_suspect`.
  * Chamar `add_npc_reply`.
  * Retornar: mensagem do jogador + mensagem do NPC + qualquer info de segredos revelados.
    ✅ *Pronto quando:* um POST nesse endpoint grava as mensagens e retorna a resposta do “NPC dummy”.

---

**T20 – API: endpoint GET /sessions/{session_id}/suspects/{suspect_id}/messages**

* Retornar lista ordenada (cronológica) de mensagens do chat daquele suspeito.
* Campos: `id`, `sender_type`, `text`, `evidence_id`, `timestamp`.
  ✅ *Pronto quando:* GET retorna histórico completo e atualizável.

---

### Bloco 5 – Progresso do suspeito e “já falei tudo que sabia”

**T21 – Função para calcular progresso do suspeito**

* Em `session_service`, criar função:

  * `calculate_suspect_progress(session_id, suspect_id) -> float | dict`
* Lógica simples:

  * Progresso = segredos core revelados / total de segredos core daquele suspeito.
    ✅ *Pronto quando:* função retorna valor consistente (0.0–1.0) para diferentes estados da sessão.

---

**T22 – Marcar suspeito como “fechado” quando todos os segredos core forem revelados**

* Estender `apply_evidence_to_suspect` para, após marcar segredos revelados:

  * Ver se todos os segredos core estão revelados.
  * Se sim, marcar `SessionSuspectState.is_closed = True`.
    ✅ *Pronto quando:* após aplicar evidências corretas, o suspeito fica `is_closed=True` na sessão.

---

**T23 – Adaptar DummyNpcAIAdapter para usar frase final ao fechar**

* Se `is_closed=True` e o jogador continuar perguntando:

  * `generate_reply` deve devolver a frase tipo “já falei tudo que sabia” (ou variação definida no suspeito).
    ✅ *Pronto quando:* para suspeito fechado, qualquer nova pergunta gera a frase final.

---

**T24 – Expor progresso do suspeito na API**

* Atualizar `GET /sessions/{session_id}` e/ou endpoint específico para suspeito para retornar:

  * `progress` (0–1 ou %)
  * `is_closed`
    ✅ *Pronto quando:* front ou cliente consegue saber, por API, o progresso com cada suspeito.

---

### Bloco 6 – Acusação final e veredito

**T25 – Implementar função de avaliação de veredito**

* Em `app/services/verdict_service.py`, criar função:

  * `evaluate_verdict(session_id, chosen_suspect_id, evidence_ids) -> VerdictResult`
* Regras:

  * Se `chosen_suspect_id != scenario.culprit_id` → `result_type="wrong"`.
  * Se igual:

    * Se contém todas evidências obrigatórias → `"correct"`.
    * Senão → `"partial"`.
      ✅ *Pronto quando:* função retorna tipo e objeto contendo info mínima (`result_type`, `missing_evidences`, etc.).

---

**T26 – Serviço para finalizar sessão**

* Função:

  * `finalize_session(session_id, chosen_suspect_id, evidence_ids) -> SessionModel`
* Deve:

  * Chamar `evaluate_verdict`.
  * Atualizar `SessionModel` com resultado, suspeito escolhido, evidências usadas.
  * Marcar `status="finished"`.
    ✅ *Pronto quando:* sessão passa de “in_progress” para “finished” corretamente.

---

**T27 – API: endpoint POST /sessions/{session_id}/accuse**

* Corpo: `{ "suspect_id": X, "evidence_ids": [ ... ] }`.
* Chamadas:

  * `finalize_session`.
  * Retornar objeto com `result_type`, descrição básica, culpado real, evidências obrigatórias.
    ✅ *Pronto quando:* é possível jogar um caso até o fim via API e receber veredito.

---

### Bloco 7 – Testes básicos

**T28 – Testes unitários: lógica de segredos**

* Testar `apply_evidence_to_suspect`:

  * Evidência correta revela segredo.
  * Evidência errada não revela nada.
    ✅ *Pronto quando:* testes passando e cobrindo pelo menos 2 casos positivos e 1 negativo.

---

**T29 – Testes unitários: avaliação de veredito**

* Testar `evaluate_verdict`:

  * Caso 1: culpado errado → `"wrong"`.
  * Caso 2: culpado certo + todas obrigatórias → `"correct"`.
  * Caso 3: culpado certo + faltando obrigatória → `"partial"`.
    ✅ *Pronto quando:* todos os cenários de teste passam.

---

**T30 – Teste de fluxo integrado (happy path)**

* Escrever teste que:

  * Carrega cenário piloto.
  * Cria sessão.
  * Faz 1–2 confrontos que revelam segredos core.
  * Chama `/accuse` com culpado e evidências corretas.
  * Recebe `result_type="correct"`.
    ✅ *Pronto quando:* esse fluxo roda de ponta a ponta sem erro.

---

Se você quiser, no próximo passo posso:

* Pegar alguns desses itens (por exemplo T4–T5–T7) e já te devolver **código Python de exemplo** para os modelos/domínio, como base real de implementação.
