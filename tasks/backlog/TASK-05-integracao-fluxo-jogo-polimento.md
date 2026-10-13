# TASK-05 — Navegação Unificada do Caso & Polimento de UX

* **ID:** `TASK-05`
* **Tipo:** Macro-Tarefa Ágil (Vertical Slice: Frontend + Backend Integration + E2E)
* **Prioridade:** P2
* **Status:** Concluído ✅

---

## 1. Contexto
Com os módulos de Design System, Dossiês de Suspeitos, Sala de Provas e Mural de Investigação desenvolvidos, é essencial que todos se integrem em um fluxo contínuo e intuitivo. O jogador não pode se sentir perdido navegando entre telas desconexas; durante o interrogatório, ele deve conseguir checar a ficha do suspeito, inspecionar o laudo de uma evidência ou abrir o mural de hipóteses com agilidade e retornar exatamente ao ponto onde estava na conversa.

---

## 2. Objetivo
Unificar a navegação de toda a investigação em uma barra tática coesa (Hub do Caso), introduzir atalhos rápidos contextuais (dentro do chat e via teclado), adicionar transições visuais suaves com estética noir e realizar uma bateria completa de testes de regressão de ponta a ponta.

---

## 3. Entregável Tangível
* **Barra de Navegação Tática do Caso:** Abas de navegação visualmente refinadas acessíveis a qualquer momento da investigação:
  * `[💬 Interrogatório]`
  * `[👤 Dossiês dos Suspeitos]`
  * `[🔎 Sala de Evidências]`
  * `[📌 Mural de Investigação]`
  * `[⚖️ Apresentar Acusação]`
* **Atalhos Contextuais no Chat:**
  * Botão de acesso rápido à ficha criminal do suspeito interrogado diretamente no topo do chat.
  * Clique prolongado ou ícone de lupa nos chips de evidência para inspecionar o laudo na Sala de Provas.
  * Botão de pino para "Enviar para o Mural".
* **Atalhos de Teclado (Power Users):** Teclas de atalho para alternar rapidamente entre abas (`[I]` Interrogatório, `[D]` Dossiê, `[E]` Evidências, `[M]` Mural).
* **Bateria de Testes Automatizados:** Suíte de testes verificando que todos os fluxos conversacionais, de acusação e de gerenciamento do caso continuam 100% íntegros.

---

## 4. Definition of Done (DoD)
1. **Fluxo Contínuo de Jogo:**
   * Alternar entre Dossiê, Sala de Provas, Mural e Interrogatório preserva o histórico de chat, texto não enviado e estado da sessão sem recarregar a página.
2. **Atalhos e Acessibilidade:**
   * Navegação funcional tanto por clique quanto por atalhos de teclado.
   * Feedback visual imediato ao usar atalhos.
3. **Consistência Visual Geral:**
   * Telas de Briefing inicial e Veredito final estilizadas no mesmo padrão de Design System Noir (com carimbos de veredito, fontes padronizadas e contraste adequado).
4. **Qualidade & Testes:**
   * Todos os testes existentes do projeto passando (`pytest`).
   * Novos testes integrados cobrindo os endpoints adicionados nas tarefas 1 a 4.

---

## 5. Subtarefas Detalhadas

### 🎨 Frontend & Navegação Unificada
- [x] **Subtarefa 5.1 — Barra de Navegação Tática do Caso:**
  * Reestruturar o header de navegação quando uma sessão estiver ativa, exibindo as 5 abas principais com ícones e labels temáticos.
  * Adicionar indicador de aba ativa com realce âmbar.
- [x] **Subtarefa 5.2 — Integração Contextual no Chat:**
  * No cabeçalho do interrogatório (`chat-header`), adicionar botão *"Ver Ficha Completa"* que leva diretamente ao perfil daquele suspeito no Dossiê.
  * Nos chips de evidência da barra de digitação, permitir visualização rápida do laudo forense sem sair do chat.
- [x] **Subtarefa 5.3 — Atalhos de Teclado e Transições:**
  * Adicionar listener global para atalhos `[I]`, `[D]`, `[E]`, `[M]` (quando o jogador não estiver digitando em campos de texto).
  * Aplicar transições de opacidade/fade suaves entre trocas de tela.

### 🧪 Testes de Ponta a Ponta & Regressão
- [x] **Subtarefa 5.4 — Testes Integrados no Backend:**
  * Executar suíte completa do pytest (`pytest tests/`) e garantir 100% de sucesso.
  * Adicionar teste de integração cobrindo o ciclo completo: Criar Sessão -> Interrogar com Evidência -> Atualizar Dossiê -> Salvar Mural -> Fazer Acusação.
- [x] **Subtarefa 5.5 — Checklist de Usabilidade:**
  * Testar o fluxo completo em resolução desktop (1920x1080 e 1366x768) e notebook/tablet.
  * Validar desempenho gráfico do mural com 15+ nós e linhas conectadas sem lentidão.
