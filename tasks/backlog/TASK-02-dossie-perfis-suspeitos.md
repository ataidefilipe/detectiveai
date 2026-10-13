# TASK-02 — Dossiê dos Suspeitos & Confronto de Evidências

* **ID:** `TASK-02`
* **Tipo:** Macro-Tarefa Ágil (Vertical Slice: Banco + Backend + Frontend)
* **Prioridade:** P1
* **Status:** Concluído (Done)

---

## 1. Contexto
Durante a investigação, o jogador precisa inspecionar o perfil psicológico e o histórico criminal de cada suspeito. Antes, a visão de dossiê resumia apenas segredos e contradições em texto simples, sem foto/avatar, sem cargo/título do suspeito no caso e sem mostrar quais evidências foram apresentadas contra aquele suspeito específico.

---

## 2. Objetivo
Criar uma tela imersiva de **Dossiê dos Suspeitos**, onde cada suspeito seja exibido como uma pasta de arquivo policial individualizada contendo imagem-template (preparada para fotos reais na Opção B), título/cargo, histórico/backstory, indicadores do estado comportamental atual e a lista completa de evidências que o jogador já usou contra ele (com indicação se foram efetivas, irrelevantes ou se quebraram uma mentira).

---

## 3. Entregável Tangível
* Uma tela/aba dedicada de "Dossiê de Suspeitos" com navegação entre os suspeitos do caso.
* Card individual no estilo Polaroid/Ficha Policial:
  * Retrato (usando o template SVG configurável, pronto para receber URL de imagem real).
  * Nome do suspeito e seu cargo/título no cenário.
  * Resumo biográfico e notas de personalidade.
  * Medidor de estado psicológico (Postura: Cauteloso, Defensivo, Sob Pressão; Paciência e Pressão).
* Seção *"Evidências Confrontadas"*:
  * Lista de todas as evidências já apresentadas a este suspeito específico na sessão atual.
  * Tag de resultado do confronto: `[💥 Mentira Quebrada]`, `[🔑 Segredo Exposto]`, `[⚡ Reação Útil]`, `[⚪ Sem Efeito]`.
* Listagem de segredos e contradições extraídos deste suspeito.

---

## 4. Definition of Done (DoD)
1. **Banco de Dados:** `SuspectModel` com `role_title` e `image_url` persistidos e migrados com segurança.
2. **Backend & API:** `GET /sessions/{session_id}/suspects` e `GET /sessions/{session_id}/suspects/{suspect_id}/dossier` retornando dados completos de perfil e `used_evidences`.
3. **Frontend & UX:** Dossiê com grid polaroid + pasta manila datilografada, alternância ágil de suspeitos em barra horizontal e histórico de evidências com carimbos.
4. **Testes:** 3 testes dedicados em `tests/api/test_suspect_dossier.py` e suíte completa de 342 testes passando com 100% de sucesso.

---

## 5. Subtarefas Detalhadas

### 🗄️ Banco de Dados & Modelos
- [x] **Subtarefa 2.1 — Enriquecimento do Modelo de Suspeitos:**
  * Adicionados `role_title` e `image_url` em `SuspectModel` (`app/infra/db_models.py`) e `SuspectConfig` (`app/domain/schema_scenario.py`).
  * Migração automática segura adicionada em `init_db()` (`app/infra/db.py`).
  * Inferência de cargos padrão e templates SVG adicionados em `scenario_loader.py`.

### ⚙️ Backend & Endpoints
- [x] **Subtarefa 2.2 — Schema e Serviço do Dossiê:**
  * Schemas `UsedEvidenceItem`, `SuspectStateSchema` e `SuspectSessionResponse` expandidos em `app/api/schemas/suspect.py`.
  * `list_session_suspects` enriquecido agregando `SessionEvidenceUsageModel` e `EvidenceModel`.
  * Rota `GET /sessions/{session_id}/suspects/{suspect_id}/dossier` implementada em `app/api/sessions.py`.

### 🎨 Frontend & Interface
- [x] **Subtarefa 2.3 — Componente de Ficha Criminal do Suspeito:**
  * Barra de seleção rápida de suspeitos com mini-avatares, nomes e cargos.
  * Card Polaroid noir com tachinha e medidor comportamental de postura, paciência e pressão.
- [x] **Subtarefa 2.4 — Painel de Evidências Confrontadas:**
  * Lista de evidências testadas contra o suspeito com contagem de apresentações e carimbos de eficácia.
  * Botão de atalho rápido direto para interrogar o suspeito.

### 🧪 Testes & Validação
- [x] **Subtarefa 2.5 — Testes Automatizados:**
  * Criado `tests/api/test_suspect_dossier.py` com 3 testes cobrindo listagem, endpoint individual e reflexo de evidências usadas.
  * Suíte completa de 342 testes executada com 100% de aprovação.
