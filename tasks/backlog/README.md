# Backlog Ágil — Redesign Visual & Experiência Noir

Este diretório contém o planejamento de engenharia e produto para a evolução visual, imersão temática e novas ferramentas investigativas do **Detective AI**.

---

## 🎯 Visão do Produto
Transformar o jogo em uma experiência investigativa *neo-noir* autêntica e profissional, focada em um **Design System coeso**, ferramentas táteis de detetive (dossiês, sala de provas e mural interativo com linhas vermelhas) e ambientação sonora diegética com jazz.

---

## 📐 Diretrizes Técnicas Adotadas
1. **Imagens:** Templates/placeholders estruturais com fallback nativo (SVG/CSS). Estrutura preparada para receber arquivos de imagem estáticos (JPG/PNG em pasta pública) no futuro (Opção B).
2. **Mural de Detetive (Whiteboard):** Implementação nativa em HTML5 Drag & Drop + camada SVG com curvas de Bézier para linhas vermelhas de barbante (Opção A — leve, sem dependências pesadas de canvas).
3. **Modularidade Frontend:** Separação limpa em arquivos modulares (`frontend/css/` e `frontend/js/`) servidos diretamente pelo FastAPI sem etapas pesadas de build ou empacotadores desnecessários.
4. **Fatias Verticais (Vertical Slices):** Cada macro-tarefa movimenta Front, Back e Banco simultaneamente e entrega um resultado utilizável e testável.

---

## 📋 Índice das Macro-Tarefas

| ID | Macro-Tarefa | Escopo | Entregável Tangível | Status |
|---|---|---|---|---|
| [TASK-01](./TASK-01-design-system-noir-audio.md) | **Fundação do Design System Noir & Jazz Audio** | Front / Back | Novo tema visual sombrio/âmbar em todo o jogo + Mini-player de jazz com controle de som e persistência. | Concluído ✅ |
| [TASK-02](./TASK-02-dossie-perfis-suspeitos.md) | **Dossiê dos Suspeitos & Confronto de Evidências** | Banco / Back / Front | Fichas criminais com fotos-template, cargos, bios e tabela detalhada de evidências confrontadas por suspeito. | Concluído ✅ |
| [TASK-03](./TASK-03-catalogo-sala-evidencias.md) | **Sala de Provas & Rastreamento Forense de Evidências** | Banco / Back / Front | Catálogo forense completo com laudos, status de uso no caso e lista de suspeitos interrogados com cada prova. | Concluído ✅ |
| [TASK-04](./TASK-04-mural-detetive-whiteboard.md) | **Mural de Investigação Interativo (Whiteboard & Red Strings)** | Banco / Back / Front | Quadro de cortiça interativo com cards arrastáveis, post-its criáveis pelo jogador, linhas vermelhas e persistência. | Concluído ✅ |
| [TASK-05](./TASK-05-integracao-fluxo-jogo-polimento.md) | **Navegação Unificada do Caso & Polimento de UX** | Back / Front / Testes | Navegação integrada com atalhos de teclado, transições suaves, testes de ponta a ponta e refinamento final. | Concluído ✅ |
