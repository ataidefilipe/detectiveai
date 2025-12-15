# 📋 Backlog — Enriquecimento Cognitivo do NPC (IA Narrativa)

---

## **US-06 — NPC com conhecimento completo do caso e de sua própria verdade** - ok

### **Por quê**

Atualmente o NPC responde de forma correta, mas superficial.
Para criar interrogatórios críveis, o NPC precisa **saber o contexto do caso, sua própria história real e as mentiras que contou**, reagindo melhor à pressão e às evidências, **sem nunca decidir o que pode ou não ser revelado**.

### **Resultado esperado**

O NPC:

* entende o caso em que está inserido
* responde de forma coerente com sua história real
* demonstra contradições, evasão e tensão
* **só revela informações quando o backend autoriza**

---

## **TS-08 — Adicionar resumo do caso como contexto cognitivo do NPC**

### **Descrição**

Permitir que o NPC conheça o **resumo do caso**, para responder de forma contextualizada, sem depender do jogador explicar tudo.

### **Tarefas**

* Adicionar campo `case_summary` no JSON do cenário
* Persistir `case_summary` no banco (ScenarioModel)
* Incluir `case_summary` no `suspect_state` enviado à IA
* Ajustar `prompt_builder` para incluir o resumo do caso como contexto fixo

### **Pronto quando**

* O NPC demonstra conhecimento do crime ao responder
* O resumo do caso não é exposto diretamente ao jogador via API
* Cenários antigos continuam funcionando sem o campo

---

## **TS-09 — Adicionar linha do tempo real do suspeito (verdade interna)**

### **Descrição**

Permitir que o NPC conheça sua **história real**, independentemente do que contou ao jogador.

### **Tarefas**

* Adicionar campo opcional `true_timeline` no JSON do suspeito
* Persistir o campo no banco (SuspectModel)
* Incluir `true_timeline` no `suspect_state` enviado à IA
* Ajustar `prompt_builder` para informar que essa linha do tempo é **conhecimento interno** do personagem

### **Pronto quando**

* O NPC responde de forma coerente com sua história real
* O NPC pode se contradizer quando pressionado
* A linha do tempo real nunca é exposta diretamente na API

---

## **TS-10 — Modelar mentiras do suspeito e evidências que as quebram**

### **Descrição**

Permitir que o NPC saiba **quais mentiras contou** e **quais evidências contradizem essas mentiras**, para reagir melhor quando confrontado.

### **Tarefas**

* Adicionar campo opcional `lies` no JSON do suspeito:

  * `statement`
  * `broken_by` (descrição da evidência)
* Persistir o campo no banco
* Incluir `lies` no `suspect_state` enviado à IA
* Ajustar o prompt para orientar:

  * evasão
  * nervosismo
  * admissão parcial quando confrontado

### **Pronto quando**

* O NPC reage de forma diferente ao ser confrontado com evidências corretas
* O NPC não revela espontaneamente as mentiras
* O comportamento não altera a lógica de progresso existente

---

## **TS-11 — Padronizar “camadas de verdade” no prompt do NPC**

### **Descrição**

Reorganizar o prompt para deixar explícitas as **camadas de conhecimento** do NPC, evitando vazamentos e respostas inconsistentes.

### **Tarefas**

* Reestruturar o `system_prompt` em blocos claros:

  * Mundo (caso)
  * Verdade do personagem
  * Mentiras
  * Segredos revelados
  * Limites de resposta
* Documentar as regras no próprio prompt
* Garantir que o prompt continue simples e legível

### **Pronto quando**

* O prompt deixa explícito o que o NPC sabe vs o que pode falar
* A IA não revela segredos fora do permitido
* O comportamento é previsível e depurável

---

## **TS-12 — Criar modo de debug do contexto enviado à IA (dev only)**

### **Descrição**

Facilitar validação e depuração do comportamento do NPC durante o desenvolvimento.

### **Tarefas**

* Criar flag `DEBUG_AI_PROMPT=true`
* Quando ativa:

  * Logar o prompt final enviado à IA
  * Logar `suspect_state` resumido
* Garantir que o debug não roda em produção

### **Pronto quando**

* Desenvolvedor consegue inspecionar exatamente o que a IA recebeu
* Nenhuma informação sensível é logada sem flag ativa
* Não afeta testes nem fluxo normal

---

## 📌 Estado do MVP após esse backlog

Com essas tasks concluídas, o MVP terá:

* NPC com **memória interna consistente**
* Interrogatórios com **tensão real**
* Mentiras que fazem sentido
* Evidências com peso narrativo
* IA **controlada pelo backend**, não solta

👉 Isso coloca seu jogo **acima de 90% dos projetos de “IA narrativa”** que existem hoje.

---

## 🔜 Próximo backlog natural (quando quiser)

* **US-07 — Reações emocionais por progresso**
* **US-08 — Epílogo narrativo após acusação**
* **US-09 — Sugestões de perguntas baseadas no estado do NPC**

Se quiser, posso **priorizar esse backlog**, **quebrar em milestones**, ou já **desenvolver a TS-08** passo a passo.
