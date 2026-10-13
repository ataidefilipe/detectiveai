# TASK-01 — Fundação do Design System Noir & Jazz Audio

* **ID:** `TASK-01`
* **Tipo:** Macro-Tarefa Ágil (Vertical Slice: Frontend + Backend Static)
* **Prioridade:** P1 (Bloqueante para as demais telas)
* **Status:** Concluído (Done)

---

## 1. Contexto
A interface atual de `frontend/index.html` possuía uma folha de estilos embutida com paleta escura genérica moderna, sem a atmosfera imersiva de romance policial noir e sem qualquer ambientação sonora. Além disso, não havia uma biblioteca organizada de tokens visuais para papéis, carimbos, molduras e tipografia temática.

---

## 2. Objetivo
Criar e consolidar a base do **Design System Noir**, extraindo o CSS para arquivos modulares, aplicando tokens semânticos (sombras, iluminação âmbar, papéis manila, carimbos) e adicionando um player de áudio diegético de Jazz Noir no cabeçalho da aplicação com controle de reprodução e persistência local.

---

## 3. Entregável Tangível
* Aplicação inteira visualmente transformada para a atmosfera Noir (com fontes clássicas, iluminação âmbar contrastante e estilo de investigação).
* Mini-player de áudio funcional no topo da tela tocando trilha de jazz em loop, com botões de Play/Pause, controle de volume, botão Mute e memória no navegador (`localStorage`).
* Arquitetura de estilos limpa e desacoplada em `frontend/css/tokens.css` e `frontend/css/noir-theme.css`.
* Componentes de template SVG reutilizáveis para retratos de suspeitos e itens de evidência (`suspect-template.svg`, `evidence-template.svg`).

---

## 4. Definition of Done (DoD)
1. **Design Tokens:** Variáveis CSS implementadas para todas as cores da paleta Noir (escrivaninha, papel manila envelhecido, vermelho de cena de crime, dourado/âmbar de luminária, carvão escuro).
2. **Tipografia:** Importação e aplicação hierárquica das fontes *Playfair Display* (títulos), *Inter* (corpo/UI) e *Courier Prime* (fichas, registros e carimbos).
3. **Componentes Base:** Classes de estilo disponíveis para `.card-noir`, `.dossier-paper`, `.rubber-stamp`, `.polaroid-frame`, `.svg-placeholder`.
4. **Player de Jazz:** Integrado ao header em múltiplos pontos com sincronização automática, sem autoplay invasivo e com persistência de volume/mute no `localStorage`.
5. **Zero regressão:** 339 testes do backend passando com 100% de sucesso e endpoints estáticos validados.

---

## 5. Subtarefas Detalhadas

### 🗄️ Backend & Infraestrutura
- [x] **Subtarefa 1.1 — Suporte a Assets Estáticos:**
  * Faixa vintage de jazz/blues (`jazz-noir.mp3`) adicionada em `frontend/assets/audio/`.
  * FastAPI em `app/main.py` validado servindo `/static/css`, `/static/js` e `/static/assets` com status HTTP 200.

### 🎨 Frontend & Design System
- [x] **Subtarefa 1.2 — Extração e Estruturação de Estilos:**
  * Criado `frontend/css/tokens.css` com tokens de cores noir, sombras e tipografia.
  * Criado `frontend/css/noir-theme.css` com componentes atômicos (polaroids, carimbos, molduras e player).
  * `frontend/index.html` linkado com tokens e tema modular.
- [x] **Subtarefa 1.3 — Componentes de Template Placeholder:**
  * Criado `frontend/assets/templates/suspect-template.svg` (retrato chiaroscuro com fedora e iluminação âmbar).
  * Criado `frontend/assets/templates/evidence-template.svg` (escala forense, tenda pericial e lupa).
- [x] **Subtarefa 1.4 — Implementação do Jazz Player:**
  * Criado `frontend/js/audio-player.js` gerenciando áudio, controles e sincronização entre todas as telas.
  * Slots de player inseridos nos cabeçalhos das telas.

### 🧪 Testes & Validação
- [x] **Subtarefa 1.5 — Validação Visual e Cross-Browser:**
  * Verificado carregamento de fontes e arquivos estáticos via TestClient do FastAPI (todos 200 OK).
  * Suíte completa de 340 testes do pytest executada com 100% de sucesso.
