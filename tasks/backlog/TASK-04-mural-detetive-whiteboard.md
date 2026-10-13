# TASK-04 — Mural de Investigação Interativo (Whiteboard & Red Strings)

* **ID:** `TASK-04`
* **Tipo:** Macro-Tarefa Ágil (Vertical Slice: Banco + Backend + Frontend)
* **Prioridade:** P1
* **Status:** Concluído ✅

---

## 1. Contexto
A investigação policial tradicional é sintetizada visualmente no famoso "quadro de detetive" (corkboard / whiteboard). Atualmente, o jogador tem apenas listas textuais e precisa manter todas as conexões mentais na cabeça. Falta um espaço espacial e tátil onde ele possa fixar fotos de suspeitos, cartas de evidências, traçar linhas de barbante vermelho ligando as peças do quebra-cabeça e colar post-its/stickers com anotações e hipóteses próprias.

---

## 2. Objetivo
Criar o **Mural de Detetive Interativo**, implementado via tecnologia nativa (HTML5 Drag & Drop / Pointer Events + camada SVG com curvas de Bézier para fios vermelhos), permitindo movimentação livre de cards, criação de post-its personalizados, conexão de barbantes vermelhos entre alfinetes e persistência integral do estado do mural por sessão no banco de dados.

---

## 3. Entregável Tangível
* Tela interativa de **"Mural do Caso" (Investigation Board)** com textura e iluminação de quadro de cortiça noir.
* **Cards Arrastáveis (Drag-and-Drop):**
  * Cards de Suspeitos (fotos polaroid com tachinha).
  * Cards de Evidências (fichas com alfinete).
  * Movimentação suave pelo tabuleiro mantendo a posição onde o jogador soltar o card.
* **Fios Vermelhos de Investigação (*Red Strings*):**
  * Camada SVG dinâmica desenhando linhas vermelhas curvas (estilo barbante de lã de cena de crime) ligando tachinhas entre si.
  * Ferramenta de conexão: clicar na tachinha do item A e depois na tachinha do item B para criar/remover o fio.
* **Stickers & Post-its Criáveis:**
  * Botão *"📌 Nova Nota"* que gera um post-it adesivo na tela.
  * Edição de texto ao clicar/digitar, escolha de cor (amarelo investigativo, rosa alerta, azul pista) e botão para remover.
* **Persistência Completa:**
  * O estado do mural (posições `x, y`, conexões ativas e textos dos post-its) é salvo automaticamente no backend e recarregado ao reabrir a sessão.

---

## 4. Definition of Done (DoD)
1. **Banco de Dados:**
   * Tabela `session_board_states` criada com campos:
     * `session_id: int` (Primary Key, Foreign Key para `sessions.id`);
     * `board_data: JSON` (armazenando nós `{ id, type, x, y }`, conexões `[{ from_id, to_id }]` e stickers `[{ id, text, color, x, y }]`);
     * `updated_at: DateTime`.
2. **Backend & API:**
   * Endpoints REST implementados:
     * `GET /sessions/{session_id}/board`: retorna o estado salvo do mural ou inicializa com posições padrão caso seja a primeira abertura.
     * `PUT /sessions/{session_id}/board`: salva/atualiza o estado do mural de forma atômica.
   * Validação de sessão existente e tratamento de concorrência/erros.
3. **Frontend & Interatividade (Opção A — Nativa):**
   * Módulo `frontend/js/board.js` e estilos `frontend/css/board.css` implementados sem bibliotecas externas pesadas de canvas.
   * Sistema de arrastar e soltar responsivo utilizando eventos de ponteiro (`pointerdown`, `pointermove`, `pointerup`).
   * Camada `<svg>` recalculando coordenadas dos fios vermelhos em tempo real durante o arraste dos cards.
   * Suporte a criação, edição e exclusão de post-its.
   * Feedback visual imediato e salvamento com debounce (para evitar sobrecarga de requisições ao backend).

---

## 5. Subtarefas Detalhadas

### 🗄️ Banco de Dados & Modelos
- [x] **Subtarefa 4.1 — Modelo de Estado do Mural:**
  * Criar `SessionBoardStateModel` em `app/infra/db_models.py`.
  * Adicionar relacionamento em `SessionModel` (`board_state = relationship(...)`).
  * Atualizar migrações / criação de tabelas automáticas no SQLite.

### ⚙️ Backend & Endpoints
- [x] **Subtarefa 4.2 — Endpoints de Leitura e Gravação do Mural:**
  * Criar schemas Pydantic em `app/api/schemas/board.py`:
    * `BoardNodeSchema`, `BoardConnectionSchema`, `BoardStickerSchema`, `BoardStateResponse`, `SaveBoardStateRequest`.
  * Implementar rotas `GET /sessions/{session_id}/board` e `PUT /sessions/{session_id}/board` em `app/api/sessions.py`.
  * Implementar serviço gerador de layout inicial padrão (espalhando os suspeitos e evidências do cenário em posições harmoniosas no tabuleiro caso o jogador ainda não tenha configurado).

### 🎨 Frontend & Canvas Nativo
- [x] **Subtarefa 4.3 — Estrutura e Estilização do Mural:**
  * Criar contêiner `#screen-board` com textura de cortiça/escrivaninha e controles superiores (Adicionar Nota, Limpar Conexões, Salvar).
  * Criar camada `<svg id="board-strings-layer">` em z-index intermediário com filtro sutil de sombra nos fios vermelhos.
- [x] **Subtarefa 4.4 — Motor de Drag-and-Drop e Linhas Vermelhas (`board.js`):**
  * Implementar gerenciador de arraste que atualiza estilo `transform: translate(x, y)` ou `left/top`.
  * Implementar função de renderização de curvas de Bézier cúbicas (`M x1 y1 C ... x2 y2`) entre os centros dos alfinetes dos itens conectados.
  * Implementar clique em alfinetes para criar novo fio ou excluir fio existente.
- [x] **Subtarefa 4.5 — Sistema de Post-its e Stickers:**
  * Implementar criação dinâmica de elementos `.sticky-note` com `<textarea>` editável.
  * Implementar botões de troca de cor (amarelo, azul, rosa) e exclusão do post-it.
- [x] **Subtarefa 4.6 — Persistência e Debounce:**
  * Sincronizar movimentações com função `saveBoardStateDebounced(sessionId)` enviando payload via `PUT /sessions/{sessionId}/board`.

### 🧪 Testes & Validação
- [x] **Subtarefa 4.7 — Testes Automatizados e Usabilidade:**
  * Teste de API em `tests/api/test_board_state.py` testando `GET` e `PUT` do estado do mural.
  * Validação no navegador: arrastar 3 cards, criar 2 post-its, ligar 2 fios vermelhos, recarregar a página e confirmar restauração precisa.
