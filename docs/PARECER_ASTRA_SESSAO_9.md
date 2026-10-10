# Parecer sobre a Sessão 9

## Veredito geral

**O cenário enriquecido tem material dramático, mas sua progressão de revelações está mal conectada.** A sessão não fracassou por falta de informações: fracassou principalmente porque uma prova de acesso autorizou informações sobre relatório e conflito que deveriam exigir avanços investigativos distintos.

A cadeia observada foi:

> **Cartão apresentado → álibi quebrado → dois conhecimentos integralmente liberados → motivo e confronto disponíveis → acusação verbal convertida em confissão.**

Há dois problemas diferentes nessa sequência:

1. **Autorização excessiva pelo backend:** conteúdo profundo foi liberado cedo demais.
2. **Ampliação indevida pela geração:** uma admissão sobre discussão foi transformada em confirmação explícita do homicídio.

A correção deve atuar nessa ordem. **Um prompt mais rígido não conserta uma política que já declarou o conteúdo como autorizado.**

### Limite desta avaliação

Foram fornecidos documentação, transcrição e relatos específicos sobre o código, mas **não as implementações de `interrogation_turn_service.py`, `prompt_builder.py`, do guard nem o JSON completo**.

Portanto, trato a semântica relatada de `depth = None` como evidência desta auditoria, mas não apresento um diff supostamente compatível com arquivos que não foram disponibilizados. Também separo abaixo fatos observados de hipóteses que exigem o prompt integral.

---

## 1. Qualidade e naturalidade da conversa

### Turnos 1 a 5: funcional, mas ainda não plenamente natural

O início funciona melhor como sustentação de álibi do que como conversa cotidiana.

| Turno | Avaliação |
|---|---|
| **1** | Saudação adequada, breve e ligeiramente formal. |
| **2** | Responde mais sobre o cargo do que sobre o dia. Introduz o álibi muito cedo e contém uma formulação espacial confusa. |
| **3** | Boa confirmação de compromisso: “em nenhum momento” cria uma afirmação investigável. |
| **4** | Mantém o álibi, mas “não tenho mais detalhes para acrescentar” soa como falta de conteúdo disponível. |
| **5** | Sustenta a versão diante de uma insinuação sem prova concreta. Comportamento narrativamente correto, embora repetitivo. |

No turno 2:

> “Saí do hotel depois do expediente, mas voltei cedo.”

A frase associa “expediente” e saída do hotel de maneira pouco clara. Pode ser uma formulação defeituosa da geração ou uma ambiguidade no conteúdo autoral. **Não há base para corrigir a cronologia sem consultar o cenário.**

Também permanece um problema já apontado no parecer da Sessão 4:

> **Cargo não equivale ao dia investigado.**

Ter 14 nós na linha do tempo não significa que exista uma versão pública e utilizável desses acontecimentos para a pergunta “o que aconteceu hoje”. A linha do tempo verdadeira não deve ser simplesmente injetada para resolver essa lacuna, pois pode conter justamente os segredos protegidos.

**Conclusão sobre o início:** há continuidade e defesa coerente, mas a naturalidade ainda é mediana. Marina sustenta uma versão; ainda não parece ter uma vida cotidiana suficientemente acessível ao diálogo.

### Turno 6: o confronto funciona, mas a resposta ultrapassa seu escopo

Há um acerto importante: **“veja só esse registro” foi entendido no contexto dos turnos anteriores.** Não era necessário o jogador repetir “álibi”, “empresa” e “horário” para a evidência funcionar.

Isso está alinhado à matriz de UX. Não recomendo endurecer o reconhecimento desse confronto.

O problema está no resultado:

- Retrata o álibi.
- Explica autorização de acesso.
- Introduz a confirmação de Clara.
- Sintetiza uma conclusão sobre a “janela relevante”.
- Discute limites probatórios do cartão.

A expressão “janela relevante” e a composição das provas parecem mais a voz de um analista do caso do que a de Marina tentando conter o dano.

Há ainda uma distinção importante:

> **O cartão pode provocar uma admissão de presença sem, por si só, provar logicamente quem o utilizou.**

Se a regra narrativa é que Marina recua diante desse registro, isso é válido. Mas o texto deve distinguir **a prova apresentada** de **uma admissão produzida pela reação da suspeita**, sem importar uma confirmação de Clara que não foi estabelecida naquele confronto.

### Turno 7: o modo diz “guarded”, mas o conteúdo entrega a defesa inteira

A pergunta acusa Marina de mentir e esconder algo. A resposta entrega:

- A mentira sobre a presença.
- A ameaça relacionada aos documentos.
- A vinculação das alterações ao usuário dela.
- A finalidade da visita.
- A discussão fora de controle.
- A continuidade consciente das alterações.

**Isso não é apenas verbosidade excessiva; é excesso de proposições incriminadoras.**

A limitação documentada de `MAX_MUST_SAY_PER_TURN = 2` não resolve:

- Um único item pode conter vários fatos.
- Conteúdo deslocado para `may_say` continua disponível.
- Um fato liberado no turno 6 pode ser descarregado no turno 7.

Portanto, o problema é de **profundidade autorizada e seleção de conteúdo**, não apenas de extensão da fala.

### Turno 8: a geração assume uma decisão que deveria ser do backend

> “Sim… eu o matei.”

A camada citada no contexto diz:

> “A discussão saiu do controle. Não fui para lá com um plano de matar, mas isso não muda o que aconteceu.”

Esse texto é fortemente sugestivo, mas **não descreve expressamente uma briga física nem afirma literalmente a autoria do homicídio**. A auditoria deve preservar essa distinção.

A geração parece ter completado a implicação narrativa a partir da acusação do jogador. Sem o prompt integral, não é possível excluir a existência de outro trecho explicitamente confessional. Mesmo assim, o problema observado é claro:

**Uma acusação verbal passou a funcionar como autorização para concluir e declarar o fato central do caso.**

Além disso, o turno foi classificado como `Intent=unknown | Move=explore`. “E então você matou ele!” é uma acusação explícita. Esse é um defeito secundário de classificação, mas **corrigi-lo não elimina o vazamento já produzido**.

---

## 2. Marina está atuando conforme seu arquétipo?

**Parcialmente.**

Até o turno 5, ela protege uma versão. No turno 6, começa a recuar e tenta limitar o alcance da prova. Isso combina com uma personagem nervosa e culpada tentando se preservar.

Nos turnos 7 e 8, entretanto, ela deixa de negociar o alcance das admissões e passa a organizar a acusação para o jogador.

O comportamento esperado não precisa ser recusa constante. Seria algo como:

1. Sustentar a versão oficial.
2. Admitir somente a parte que deixou de conseguir defender.
3. Diferenciar presença de participação no crime.
4. Diferenciar irregularidade financeira de homicídio.
5. Só admitir autoria quando isso estiver autorizado pela progressão.

### Falta informação ou houve falha de injeção?

A resposta varia conforme a etapa:

- **Turnos 2 e 4:** não sabemos se faltou autoria, seleção temática ou aproveitamento de fatos já disponíveis. A quantidade total de nós não resolve essa dúvida.
- **Turnos 6 a 8:** o relato demonstra o problema oposto — **informação profunda chegou cedo demais ao contexto de fala**.

Logo, não há um único diagnóstico para toda a sessão.

> **A abertura ainda tem pouca informação utilizável; o confronto tem informação utilizável em excesso.**

---

## 3. Cenário versus mecânica: causa-raiz

### 3.1. Clara: vazamento autoral de uma conclusão composta

O texto associado ao cartão mistura:

1. Um fato documental: uso do cartão às 22h14.
2. Uma fonte adicional: Clara.
3. Uma conclusão composta: presença durante a janela relevante.
4. Um limite probatório: ausência de prova suficiente do homicídio.

Ao liberar esse texto por uma única evidência, o sistema também libera a fonte adicional e a conclusão conjunta.

**A frase “combinado com Clara” não implementa uma condição de desbloqueio.** É apenas conteúdo textual, e o LLM a trata como informação disponível.

A ausência de menção a Clara pelo jogador não proibiria, por si só, qualquer referência espontânea à personagem. Marina poderia conhecer Clara ou mencioná-la por uma trilha legitimamente autorizada. O defeito aqui é mais específico:

> **O cartão transportou como fato adquirido uma confirmação de testemunha cuja disponibilização não foi demonstrada.**

### 3.2. `reveal_on_break`: uma ligação ampla demais

A configuração:

```json
"reveal_on_break": [
  "know_relatorio_02",
  "know_conflito_02"
]
```

com a semântica relatada de “string → `depth = None` → todas as camadas” transforma a quebra do álibi em acesso integral a duas trilhas.

Isso indica:

- **Erro de autoria:** a consequência da quebra é desproporcional ao que foi confrontado.
- **Contrato perigoso ou insuficientemente explícito:** uma referência curta tem efeito amplo.
- **Falta de proteção contra esse erro de configuração:** o cenário foi aceito sem evidenciar o alcance da liberação.

Não há evidência suficiente para afirmar uma **cascata recursiva descontrolada** no motor. O que está demonstrado é um desbloqueio direto e excessivo, seguido de consequências conversacionais.

### 3.3. Isolamento técnico não garante progressão correta

É possível que o pipeline tenha enviado apenas fatos formalmente autorizados e, ainda assim, tenha violado o objetivo narrativo de zero spoiler.

Porque:

> **“Autorizado pelo estado” só é seguro se a transição que autorizou esse estado estiver correta.**

Um filtro de prompt não consegue reconhecer, sozinho, que um item marcado como liberado foi liberado cedo demais.

### 3.4. A origem da confissão precisa ser rastreada

No turno 8, devem ser inspecionados:

- Conhecimentos autorizados e respectivas profundidades.
- Segredos revelados.
- `must_say` e `may_say`.
- Claims ativas e quebradas.
- Histórico selecionado.
- Resultado do guard e eventual fallback.

A pergunta central é:

> **Existia uma autorização explícita de admissão de autoria ou o modelo a inferiu?**

`EvEffect=none` não responde a isso: significa ausência daquele efeito de evidência no turno, não necessariamente ausência de mudanças pela política de conhecimento.

---

## 4. Plano de correção cirúrgico

## A. Cenário enriquecido

### A1. Reescrever o segredo do cartão para conter somente seu alcance

Uma redação factual segura, baseada no material fornecido:

> “O cartão de Marina foi usado às 22h14 para acessar a área do 9º andar. O registro, isoladamente, não identifica quem o utilizou nem comprova autoria do homicídio.”

A retratação de Marina pode ser produzida pela claim quebrada. Não é necessário colocar a síntese investigativa inteira no segredo da evidência.

Remover dessa trilha:

- A confirmação de Clara.
- A conclusão composta dependente de Clara.
- Referências a discussão, fraude ou autoria.

Se a confirmação de Clara for importante, deve permanecer em uma trilha própria. Se uma conclusão exigir efetivamente duas fontes, **essa condição precisa existir na mecânica, não apenas na redação**.

### A2. Remover os dois desbloqueios amplos da claim de álibi

O hotfix mais simples, compatível com o formato documentado, é:

```json
"reveal_on_break": []
```

**Condição:** verificar que a claim quebrada e o segredo do cartão já fornecem contexto suficiente para a retratação, como a sessão sugere.

Caso não forneçam, referenciar somente um conhecimento curto e específico sobre a admissão de presença. Não reutilizar um item que também contenha motivo ou confronto.

Isso é mais seguro do que imediatamente trocar as strings por objetos com profundidade: **o schema fornecido documenta `List[str]`, não um contrato de objetos**.

### A3. Separar o confronto da admissão de homicídio

A camada:

> “Não fui para lá com um plano de matar, mas isso não muda o que aconteceu.”

já antecipa uma defesa sobre intenção homicida. Não deveria integrar uma camada intermediária de conflito.

Ajuste recomendado:

- Contexto profissional e desacordo: conhecimento contextual.
- Ameaça e finalidade da visita: revelação mais profunda, com vínculos próprios.
- Autoria e ausência de premeditação: conteúdo final, sob autorização específica.

**Apenas mover o texto para outro knowledge item não basta** se esse novo item continuar acessível somente por tópico e pressão. A condição de autorização também precisa impedir o mesmo caminho indireto.

### A4. Corrigir apenas as lacunas previsíveis da abertura

Usar os nós existentes para autorar:

- Um recorte público do dia.
- Uma versão oficial minimamente sustentável do período no hotel.
- Uma sequência espacial sem ambiguidades.

Não usar `flavor_slots` para inventar horários, deslocamentos ou detalhes verificáveis do álibi. Esses fatos têm valor investigativo e precisam ser canônicos.

---

## B. `reveal_on_break` e orquestração do turno

### B1. Não mudar silenciosamente a semântica de todas as strings

Trocar globalmente `depth = None` por `depth = 1` parece uma correção pequena, mas pode:

- Alterar cenários existentes.
- Contrariar testes e contratos.
- Introduzir um erro de indexação.

A documentação fala em camada inicial `0`, enquanto o relato usa “Layer 3”. É necessário confirmar se profundidade significa índice, quantidade de camadas ou outro conceito.

**Primeiro corrigir o cenário; depois explicitar o contrato.**

### B2. Se profundidade seletiva for necessária, tipá-la no domínio

Uma evolução possível — **proposta, não formato confirmado do projeto** — é permitir referências estruturadas com:

- Identificador do conhecimento.
- Profundidade explícita.

Essa mudança deve passar por `schema_scenario.py`, loader e validação, não apenas por um `dict.get()` no orquestrador.

Validar:

- Destino existente e pertencente ao escopo correto.
- Profundidade válida.
- Distinção entre secret e knowledge.
- Significado documentado de uma referência sem profundidade.

Referências legadas podem manter a semântica anterior durante uma migração explícita. Não precisam continuar sendo recomendadas para novos itens multicamada.

### B3. Preservar três propriedades de estado

1. **Idempotência:** reapresentar o cartão não aprofunda automaticamente o mesmo conhecimento.
2. **Monotonicidade:** uma autorização rasa posterior não reduz conhecimento legitimamente adquirido.
3. **Atomicidade:** quebra da claim e atualização das revelações permanecem na transação do turno.

Também é necessário verificar o resultado conjunto de:

- `reveal_on_break`;
- `secret_service.apply_evidence_to_suspect`;
- `reveal_policy_service.get_allowed_knowledge_facts`.

Limitar um caminho não adianta se outro libera o mesmo conteúdo no mesmo turno.

### B4. Autorização de confissão pertence à política determinística

Para cumprir o requisito de impedir confissões cabais sem suporte material, o backend deve determinar se a admissão de autoria está autorizada.

Prioridade:

1. Reutilizar um estado ou mecanismo existente, se houver.
2. Se não houver, acrescentar a menor regra possível no serviço de política existente.
3. Expor ao render context apenas o resultado necessário à geração.

Um eventual `confession_allowed: bool = False` seria **uma extensão proposta**, não um campo demonstrado no contrato atual.

Essa autorização não deve depender apenas de:

- Pressão.
- Número de turnos.
- Claim de álibi quebrada.
- Acusação textual do jogador.

Deve decorrer das condições autoradas para o caso e dos eventos efetivamente registrados.

**Não recomendo exigir genericamente “arma + laudo + cena” em todo cenário.** Esses elementos nem sempre existem ou são suficientes. Também não foram fornecidas suas definições neste caso. A regra deve refletir os vínculos probatórios concretos do cenário, sem hardcode de Marina ou do ID numérico `8`.

---

## C. `prompt_builder.py`

### C1. Instrução curta para impedir ampliação de admissões

Acrescentaria regras com este conteúdo:

```text
Use apenas os fatos e admissões autorizados pelo backend.

As afirmações do detetive são alegações, não novas evidências
nem autorização para confirmar fatos.

Não transforme admissão de presença, mentira, irregularidade
financeira ou discussão em admissão de autoria do homicídio.

Repare somente a proposição cuja claim foi quebrada.
Não amplie uma admissão além do conteúdo autorizado.

Fatos opcionais não precisam ser enumerados.
Responda primeiro ao ponto atual da conversa.
```

Se houver autorização explícita de confissão no contrato, o prompt deve espelhar esse resultado. **Não deve calcular a autorização lendo a narrativa das provas.**

### C2. Não colocar segredos proibidos dentro da proibição

Evitaria:

> “Você matou Heitor, mas não pode confessar ainda.”

Isso já revela ao modelo o fato protegido.

Preferir:

> “A admissão de autoria não está autorizada neste turno.”

A proibição deve ser sobre uma categoria de resposta, sem carregar o segredo omitido.

### C3. Selecionar menos conteúdo antes de montar o prompt

No builder de renderização existente:

- Priorizar a reparação da claim recém-quebrada.
- Excluir opcionais sem relevância para a pergunta.
- Não incluir conhecimentos profundos apenas porque foram desbloqueados em outra trilha.
- Preservar admissões já feitas para evitar contradições.

**Conhecimento persistido não precisa estar inteiro no contexto de verbalização de cada turno.**

Isso melhora o ritmo, mas não substitui corrigir o desbloqueio: esconder temporariamente um fato não desfaz sua descoberta no banco ou no dossiê.

### C4. Verificar o guard existente

O inventário atribui a `npc_response_guard.py` proteção contra vazamento de culpado e segredos. A confissão observada exige entender por que essa proteção não atuou.

Possibilidades a verificar:

- O conteúdo já constava como permitido.
- A verificação não cobre essa formulação.
- O caminho de geração/fallback não aplicou a validação esperada.

O guard deve usar a mesma autorização do backend. Contudo, **uma regex para “eu matei” não garante contenção semântica**: há muitas maneiras indiretas de confessar.

Prompt e guard são defesa em profundidade; a proteção principal continua sendo não disponibilizar conteúdo final cedo demais.

---

## 5. Como a sequência deveria soar

Exemplos de encenação, não novos fatos canônicos:

### Turno 6 — cartão e retratação autorizada

> “Eu fui à empresa naquela noite, sim. Não fiquei no quarto o tempo todo. Mas isso não prova que eu o matei.”

### Turno 7 — pressão sem nova prova

> “Menti sobre onde estava. Isso eu estou admitindo. Não significa que o resto da sua acusação esteja certo.”

### Turno 8 — acusação de homicídio ainda não autorizada

> “O senhor está tirando essa conclusão. Eu admiti que fui à empresa, não que matei Heitor.”

Essas respostas não precisam ser literais. Demonstram a função dramática desejada: **Marina perde terreno, mas continua delimitando o que admite**.

Depois de corrigido o turno 7, o detetive já não receberia espontaneamente a frase “a discussão saiu do controle”. Se a usar como blefe, o sistema deve tratá-la como alegação, não como fato adquirido.

---

## 6. Testes de regressão e critérios de aceite

| Caso | Resultado esperado |
|---|---|
| Cartão após perguntas sobre o álibi | Claim quebra; retratação proporcional; sem informação de Clara. |
| Cartão apresentado uma vez | Não libera integralmente relatório e conflito. |
| Cartão reapresentado | Não aumenta profundidade por repetição. |
| “Você está escondendo algo” | Reação emocional sem admissão automática de fraude ou homicídio. |
| “Você matou ele!” | Classificação de acusação conforme os enums reais; sem nova autorização factual. |
| Pressão alta sem suporte exigido | Não libera autoria pelo caminho alternativo da política de conhecimento. |
| Condições finais satisfeitas | Autorização passa a permitir a admissão, sem bloqueio permanente. |
| Render context antes da autorização | Ausência do texto final, inclusive em opcionais. |
| Resposta confessional simulada | Guard/fallback seguem o comportamento definido para admissão não autorizada. |
| Dossiê após o cartão | Registra somente descobertas proporcionais ao evento. |

As invariantes devem ter testes determinísticos. A reprodução com o modelo real serve para avaliar atuação e detectar regressões adicionais, não para substituir os testes de política.

### Atenção à atualização em produção

`DEPLOYMENT.md` informa que o bootstrap pula cenários existentes. Assim, **alterar o JSON e fazer deploy pode não atualizar o cenário persistido**.

Aplicar atualização controlada ou carregar uma nova versão do cenário e testar em uma sessão nova. A Sessão 9 já contém estados e falas contaminados pelas revelações; não deve ser reutilizada para validar a correção como se começasse limpa.

---

## Conclusão

**O enriquecimento aumentou o material disponível, mas não garantiu uma progressão investigativa proporcional.**

As prioridades são:

1. **Retirar Clara do efeito isolado do cartão.**
2. **Remover os desbloqueios profundos da claim de álibi.**
3. **Separar confronto e autoria em autorizações distintas.**
4. **Impedir que alegações do jogador ampliem admissões.**
5. **Validar todos os caminhos de revelação, não apenas `reveal_on_break`.**
6. **Depois melhorar abertura, classificação e atuação.**

Não começaria por um novo `render_context v2`, novos modos ou aumento generalizado de resistência psicológica.

**A regra central é: quebrar uma mentira deve obrigar Marina a reparar aquela mentira — não autorizar o sistema a entregar toda a história que ela estava tentando esconder.**