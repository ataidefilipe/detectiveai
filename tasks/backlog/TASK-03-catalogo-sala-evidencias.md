# TASK-03 — Sala de Provas & Rastreamento Forense de Evidências

* **ID:** `TASK-03`
* **Tipo:** Macro-Tarefa Ágil (Vertical Slice: Banco + Backend + Frontend)
* **Prioridade:** P1
* **Status:** Concluído ✅

---

## 1. Contexto
No jogo atual, as evidências aparecem apenas como pequenos botões horizontais ("chips") na barra de chat ou em uma lista simples de texto no hub de investigação. O jogador não tem uma "Sala de Evidências" (Evidence Locker) onde possa inspecionar os objetos apreendidos em detalhe, ver sua imagem ou ilustração técnica, ler seu laudo forense completo e acompanhar seu status global no caso: **se a evidência já foi apresentada a alguém, a quais suspeitos foi apresentada e se surtiu algum efeito revelador**.

---

## 2. Objetivo
Criar a tela de **Sala de Provas / Catálogo de Evidências**, estruturada como um fichário do laboratório pericial, onde cada evidência possui uma imagem-template, título oficial, laudo descritivo e indicadores de rastreamento de uso (status: *Intacta/Não Utilizada* ou *Apresentada*, listando todos os suspeitos contra os quais já foi testada e o resultado de cada confronto).

---

## 3. Entregável Tangível
* Nova tela/módulo navegável: **"Sala de Provas" (Evidence Locker)**.
* Grid de cartões de evidência estilizados como sacos de prova forense / etiquetas de custódia:
  * Imagem ilustrativa técnica (usando template SVG estilizado de evidência com régua/marcador pericial, preparado para JPG/PNG na Opção B).
  * Código da evidência (ex.: `EV-01`) e Título oficial.
  * Laudo pericial detalhado com informações da cena do crime.
* Painel de Rastreabilidade de Uso:
  * Badge de status principal: `[🟢 Intacta - Não Apresentada]` ou `[🔍 Apresentada em Investigação]`.
  * Se já foi usada: Chips/Tags listando cada suspeito interrogado com ela, indicando a reação obtida (ex.: *Marina Souza: 💥 Quebrou Álibi*; *Rogério Lima: ⚪ Sem reação*).
* Filtros rápidos no topo da tela: "Todas", "Apenas Não Usadas", "Já Utilizadas".

---

## 4. Definition of Done (DoD)
1. **Banco de Dados:**
   * `EvidenceModel` suporta campo `image_url` (String, nullable) com fallback para template placeholder SVG.
   * Relações em banco permitem consultar facilmente o histórico de apresentação da evidência (`SessionEvidenceUsageModel`).
2. **Backend & API:**
   * Enriquecimento do endpoint `GET /sessions/{session_id}/evidences` para retornar para cada evidência:
     * `id`, `name`, `description`, `evidence_code`, `image_url`;
     * `is_used`: booleano indicando se foi usada em pelo menos um suspeito;
     * `usages`: lista com `{ suspect_id, suspect_name, was_effective, effect_type, times_presented, last_used_at }`.
   * Teste de integração de API validando a consistência dos dados de uso de evidência.
3. **Frontend & UX:**
   * Interface imersiva de laboratório forense / armário de evidências policiais com tema noir.
   * Modal ou expansão de card permitindo leitura do laudo técnico ampliado.
   * Filtros e ordenação funcionando sem recarregar a página.

---

## 5. Subtarefas Detalhadas

### 🗄️ Banco de Dados & Modelos
- [x] **Subtarefa 3.1 — Estrutura de Imagem e Metadados de Evidência:**
  * Adicionar campo `image_url` em `EvidenceModel` (`app/infra/db_models.py`).
  * Atualizar o carregador de cenários para preencher códigos e referências de imagem padrão para as 13 evidências do cenário piloto.

### ⚙️ Backend & Endpoints
- [x] **Subtarefa 3.2 — Enriquecimento do Schema de Evidências:**
  * Atualizar `EvidenceResponse` em `app/api/schemas/evidence.py` para incluir:
    * `evidence_code: Optional[str]`
    * `image_url: Optional[str]`
    * `is_used: bool`
    * `usages: List[EvidenceUsageDetailSchema]` contendo nome do suspeito, eficácia e tipo de efeito.
  * Modificar a rota `GET /sessions/{session_id}/evidences` em `app/api/sessions.py` para fazer a agregação das tabelas `session_evidence_usages` e `suspects`.

### 🎨 Frontend & Interface
- [x] **Subtarefa 3.3 — Criação da Tela da Sala de Provas:**
  * Estruturar a seção `#screen-evidence-locker` em `frontend/index.html`.
  * Criar cards forenses com moldura de etiqueta pericial e template SVG do item.
  * Implementar visualização detalhada do laudo.
- [x] **Subtarefa 3.4 — Renderização do Rastreamento de Uso:**
  * Implementar a lista de suspeitos confrontados dentro de cada card de evidência.
  * Adicionar barra de filtros rápidos (Todas / Não Usadas / Usadas).

### 🧪 Testes & Validação
- [x] **Subtarefa 3.5 — Testes de Integração e Regressão:**
  * Criar teste em `tests/api/test_evidence_locker.py` garantindo que, quando o jogador usa a evidência em um suspeito, a resposta de `GET /sessions/{session_id}/evidences` atualiza `is_used = true` e inclui o suspeito na lista de `usages`.
