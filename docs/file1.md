

O teste com a Marina mostra um problema central: a IA está sendo usada como **boca do backend**, mas o backend ainda está entregando para ela um contexto que empurra respostas muito defensivas, muito genéricas e muito repetitivas. O resultado não soa como “suspeita nervosa escondendo algo”; soa como “NPC travado em modo recusa”. Isso bate com o seu piloto: Marina deveria ser meticulosa, ansiosa, tentar parecer calma, ter conflito com a vítima e conhecimento em camadas sobre relatório e conflito. No entanto, no diálogo ela só recusou. Isso empobrece justamente a parte mais importante do jogo: a conversa.  

Pelo cenário, a Marina **não é uma parede muda**. Ela tem:

* um `initial_statement` defensivo, mas não final;
* `knowledge` em camadas sobre o relatório;
* um conflito progressivo com a vítima;
* um álibi frágil;
* um perfil de alta receptividade a empatia e alta irritabilidade a repetição.
  Isso pede uma personagem que **responde, desvia, corta detalhes, racionaliza, minimiza, corrige, escapa por tangente e só fecha completamente quando pressionada demais** — não alguém que responde “prefiro não responder” para quase tudo. 

Além disso, o próprio backend já aponta duas causas estruturais para a artificialidade atual: o jogo hoje ainda incentiva detecção de tópico por palavra-chave e encaixe de evidência, em vez de sustentar uma conversa realmente investigativa; e a memória conversacional entregue à IA ainda é incompleta ou subaproveitada, deixando a fala genérica.  

## Diagnóstico do que está acontecendo na prática

No seu transcript, há três falhas combinadas:

**1. “Evasivo” virou “recusa seca”.**
O prompt atual mapeia modos como `evasive`, `deny`, `guarded`, `pressured_deflection` etc. Se a instrução de modo é muito forte e o contexto útil é pequeno, a LLM converge para a forma mais segura: recusar. 

**2. Falta obrigação de avançar minimamente a conversa.**
A prompt builder hoje tem seção obrigatória para `new_knowledge_this_turn`, mas fora isso a IA ainda pode responder curto, repetitivo e estéreo. Nada força o suspeito a “dar alguma coisa” mesmo quando não pode revelar o segredo principal. 

**3. O backend está pensando mais em controle do que em ritmo dramático.**
Os feedbacks `out_of_context`, `reaction_only`, `topic_signal`, `npc_shift` são bons para sistema, mas a boca do NPC precisa funcionar como fala humana. Se a lógica de retenção é boa mas a superfície verbal é pobre, o jogador sente parser, não personagem. 

## Princípio que eu adotaria

A IA deve receber **somente o que precisa saber**, mas esse “precisa saber” não é só conteúdo factual. Ela também precisa saber:

* o que **não pode** dizer;
* o que **pode insinuar**;
* o que **deve responder parcialmente**;
* qual é a **postura emocional atual**;
* qual foi a **última pergunta do jogador**;
* qual é o **objetivo dramático da resposta** neste turno.

Sem isso, ela escolhe a forma mais barata de obedecer: negar ou recusar.

## Estratégia-mãe: trocar “permissão de conteúdo” por “faixa de resposta”

Hoje a sua estrutura está muito perto de:

> “estes fatos podem ser ditos; estes não podem.”

Isso controla spoiler, mas não naturalidade.

Eu mudaria para:

> “neste turno, a resposta deve cair numa faixa comportamental.”

Exemplo de faixas:

* responder normalmente, mas superficialmente;
* responder e minimizar;
* responder com detalhe lateral, evitando o centro;
* corrigir um detalhe e esconder o resto;
* negar um ponto, mas admitir o contexto;
* admitir desconforto sem admitir culpa;
* perder a compostura por um instante;
* reparar contradição.

Essas faixas são melhores do que simplesmente `evasive` ou `deny`, porque dão **forma humana** ao silêncio.

## Estratégias concretas

### 1. Toda resposta precisa entregar alguma utilidade

Regra de ouro: o suspeito raramente deve responder com recusa pura. Mesmo quando bloqueado, ele precisa entregar pelo menos um destes tipos de valor:

* um detalhe periférico verdadeiro;
* uma emoção;
* uma minimização;
* uma correção;
* uma opinião sobre outra pessoa;
* uma justificativa;
* uma tentativa de encerrar;
* uma mudança de assunto plausível.

Exemplo ruim:

> “Prefiro não responder.”

Exemplo melhor:

> “Isso é assunto do financeiro. Eu não cuidava sozinha desses relatórios. Havia revisão, pressão, cobrança… e sinceramente eu já estava exausta daquela situação.”

Ainda não entregou o segredo principal, mas moveu a conversa.

Isso combina com as `content_layers` da Marina sobre relatório e conflito. O ideal é que a IA revele camadas periféricas antes do núcleo incriminador. 

### 2. Separar “o que ela sabe” de “o que ela está disposta a admitir”

Sua estrutura de `knowledge` em camadas é boa, mas eu não deixaria a IA decidir diretamente a partir dela. Eu criaria, por turno, uma lista já curada:

* `admissible_now`: frases que ela pode dizer agora;
* `sensitive_but_deflectable`: coisas que ela pode tangenciar;
* `forbidden_now`: coisas que não pode admitir;
* `preferred_deflections`: rotas de fuga temáticas.

Para a Marina, em pergunta sobre dados contábeis, algo assim:

* admissible_now:

  * “O relatório estava sendo revisado naquela semana.”
  * “Havia inconsistências nos números.”
* sensitive_but_deflectable:

  * “A vítima me pressionava sobre aquilo.”
* forbidden_now:

  * “Eu adulterei os relatórios.”
* preferred_deflections:

  * “isso era tratado por mais de uma pessoa”
  * “a pressão vinha de cima”
  * “não era simples como parece”

Isso gera naturalidade com controle forte.

### 3. Trocar respostas categóricas por respostas com gradiente

A Marina não deveria ir de “já disse tudo” para “não respondo” em sequência. Ela deveria oscilar.

Sugestão de progressão por tema:

* primeiro contato com tópico: resposta curta, plausível, superficial;
* segunda investida: leve irritação ou cautela, mas mais detalhe lateral;
* terceira investida bem feita: fissura emocional ou correção defensiva;
* confronto forte: admissão parcial ou reparo de contradição.

No seu transcript, a repetição da pergunta sobre dados contábeis produziu quase a mesma resposta. Isso mata a sensação de progresso. A repetição deveria mudar **textura** da fala mesmo quando o conteúdo central não muda. 

### 4. Cada suspeito precisa de “mecanismos de fuga” próprios

Naturalidade não vem só de contexto factual. Vem de estilo de evasão.

Para Marina, eu definiria 5 mecanismos preferenciais:

* burocratizar;
* minimizar;
* dizer que estava sob pressão;
* deslocar culpa para ambiente/cultura da empresa;
* ficar ofendida por insinuação direta.

Assim, quando a IA não puder revelar algo, ela não recusa de modo genérico; ela foge **como a Marina**.

### 5. A pergunta aberta não deve ser punida com secura

No transcript, “me conte o que aconteceu nessa noite” caiu numa resposta morta, e o sistema ainda sinalizou que a pergunta foi muito aberta. Isso pode ser verdade como sistema, mas não deveria produzir NPC árido. O suspeito pode responder a pergunta aberta com recorte.

Exemplo:

> “Foi uma noite caótica. Eu fiquei resolvendo pendências, vi gente entrando e saindo, e no fim só queria ir embora. Se você quer saber de um horário específico, pergunta direto.”

Isso:

* mantém a personagem;
* não entrega tudo;
* orienta o jogador;
* parece conversa humana.

### 6. A IA precisa receber o “alvo dramático do turno”

Além de `response_mode`, eu passaria algo mais preciso, como:

* `turn_goal = "stall_but_keep_conversation_alive"`
* `turn_goal = "admit_context_hide_action"`
* `turn_goal = "protect_alibi"`
* `turn_goal = "show_irritation_after_repetition"`
* `turn_goal = "leak_pressure_from_victim"`

Isso é muito mais útil do que só `evasive`. O modelo consegue soar natural quando sabe **qual função dramática a fala deve cumprir**.

### 7. Não mande o histórico inteiro; mande o histórico certo

O problema não é token alto. É contexto ruim.

O ideal é mandar:

* a última pergunta do jogador;
* as 3–6 últimas trocas relevantes;
* mensagens “pinned” com admissões já feitas;
* fatos quebrados/claims quebradas;
* estado emocional atual;
* o bloco pequeno de fatos admissíveis agora.

O próprio prompt builder já sugere uma ideia de pinning por `effective_message_ids`, além de usar segredos/knowledge/claims quebradas. O caminho certo é melhorar a seleção, não despejar tudo. 

### 8. O modelo precisa de instrução explícita contra respostas vazias

Eu colocaria no prompt algo como regra estrutural:

* nunca responder apenas com recusa seca;
* quando não puder responder diretamente, responder com desvio plausível + detalhe periférico + tom emocional;
* manter 1 a 4 frases;
* evitar repetir a mesma construção duas vezes seguidas;
* se a pergunta tocar tema sensível, mostrar desconforto antes de negar ou minimizar.

Isso não aumenta muito token e muda bastante a qualidade.

### 9. Usar “camadas de revelação lateral”

Sua `knowledge` já está organizada em `content_layers`. Eu usaria isso melhor.

Para o tópico `relatorio_contabil` da Marina, a fala deveria seguir algo como:

* camada 1: contexto neutro;
* camada 2: contexto tenso;
* camada 3: aproximação do comprometimento.

Exemplo de progressão:

1. “Aquele relatório estava sendo revisado, sim.”
2. “Tinha coisa errada ali, e eu não fui a única a perceber.”
3. “Ele sabia das irregularidades e me pressionava.”
4. “Você está tentando me empurrar tudo, como se eu tivesse agido sozinha.”

Perceba que isso mantém naturalidade e cria arco.

### 10. Não transformar toda evidência em “chave que abre cofre”

Quando o jogador mostra a evidência, a fala não precisa ir direto para revelação ou recusa. Ela pode:

* contestar interpretação;
* corrigir detalhe;
* admitir parte e negar o resto;
* mudar o peso moral do fato.

Isso é especialmente importante para `cartao_acesso` e `relatorio_contabil` no piloto. Essas evidências deveriam gerar falas muito mais ricas do que “não vou responder”. 

## O que eu mudaria no contrato enviado para a IA

Eu reduziria para um contexto enxuto, mas de alta densidade:

```json
{
  "character": {
    "name": "Marina Souza",
    "persona": "meticulosa, ansiosa, tenta parecer calma",
    "speech_style": ["formal", "contida", "fica ríspida sob pressão"]
  },
  "scene": {
    "case": "morte em sala trancada",
    "player_question": "me fale sobre o que estava acontecendo com os dados contábeis",
    "topic": "relatorio_contabil",
    "turn_goal": "admit_context_hide_personal_involvement",
    "stance": "guarded",
    "emotion": "irritada, mas controlada"
  },
  "memory": {
    "already_admitted": [
      "o relatório estava sendo revisado naquela semana"
    ],
    "broken_claims": [],
    "recent_relevant_dialogue": [
      "Jogador perguntou sobre a noite",
      "Jogador perguntou horário de chegada"
    ]
  },
  "content_policy": {
    "must_include_one_of": [
      "havia inconsistências nos números",
      "era um assunto sensível no setor"
    ],
    "may_hint": [
      "a vítima pressionava pessoas",
      "o ambiente estava tenso"
    ],
    "must_not_reveal": [
      "Marina adulterou os relatórios",
      "Marina matou a vítima"
    ]
  },
  "response_rules": {
    "max_sentences": 4,
    "do_not_be_silent": true,
    "avoid_repeating_previous_refusal": true,
    "sound_human": true
  }
}
```

Isso é pequeno, controlado e muito melhor para naturalidade.

## Estratégia específica para a Marina do piloto

Para esse caso, eu trataria Marina como personagem de “controle rachando”. O arco dela deveria ser:

* começo: contida, quer parecer colaborativa;
* meio: burocrática, seca, tenta enquadrar a conversa;
* quando toca relatório: desconforto técnico primeiro, moral depois;
* quando toca vítima: emoção reprimida;
* quando toca álibi: contradição;
* quando confrontada com cartão/testemunho: reparo de história;
* perto do fim: frases mais curtas, menos elegantes, mais pessoais.

O piloto dá material suficiente para isso: tensão com a vítima, irregularidades, ameaça de demissão, álibi falso e perfil emocional. 

## O que evitar

Evite quatro coisas:

**1. Modo único por turno.**
“evasivo” sozinho é grosso demais.

**2. Recusa literal como fallback padrão.**
Isso deve ser raro, quase final de linha.

**3. Excesso de metainstrução sistêmica visível no texto.**
O jogador não deve sentir que encostou num `out_of_context`; deve sentir que a pessoa fugiu.

**4. Resposta sem microavanço.**
Toda fala precisa mudar algo: informação, emoção, hipótese ou atmosfera.

## Uma heurística prática para o backend

Antes de gerar a fala, faça esta pergunta:

> “Se eu proibisse a LLM de dizer ‘não sei’, ‘já falei’, ‘prefiro não responder’, ela ainda conseguiria responder este turno?”

Se a resposta for não, o contexto do turno está pobre demais.

## Resultado esperado

Quando isso estiver bom, a conversa com Marina deve soar assim:

* o jogador pergunta algo amplo;
* ela recorta o assunto;
* o jogador insiste;
* ela começa a mostrar incômodo específico;
* evidência não vira senha, vira alavanca;
* o jogador percebe padrões, não flags;
* a admissão parcial vem como rachadura, não como unlock.

Esse é o ponto em que a conversa deixa de ser “interface para sistema” e vira de fato “interrogatório”.

## Síntese objetiva

A estratégia mais forte é esta:

**manter o backend soberano sobre o que pode ser revelado, mas passar para a IA não só fatos permitidos — passar também o papel dramático da resposta, a rota de fuga preferida, o mínimo avanço obrigatório e a memória relevante já consolidada.**

Isso preserva controle e aumenta muito a naturalidade. O seu piloto já tem material para isso; o que falta é parar de tratar evasão como recusa e começar a tratá-la como comportamento humano controlado.   

No próximo passo, eu posso te devolver um desenho técnico de `render_context v2` e um prompt de sistema novo, já pensado para Marina e para os outros suspeitos.


Seu objetivo muda a hierarquia do sistema.

Você não está pedindo “mais controle”. Está pedindo **mais fluidez verbal com contenção informacional**. Isso significa que o backend deve continuar soberano sobre o que é verdade, o que pode ser dito e o que ainda não pode sair, mas ele precisa parar de usar esse controle para **estrangular a fala**. Pelo código atual, o estrangulamento vem de três lugares: o `determine_response_mode` joga facilmente para `deny`, `evasive` e `guarded`; o `build_npc_prompt` reforça esses modos com instruções muito secas; e a revelação de conhecimento ainda depende demais dos `detected_topics` do turno, mesmo existindo sinais de contexto herdado e tópico ativo nas versões mais novas.    

A boa notícia é que a base certa já existe. Você já tem `claims`, `broken_claims`, `active_topic_id`, `context_inherited`, `move_type`, `state_transition`, `knowledge` em camadas e um `render_context` próprio para a IA. O que falta não é inventar outro sistema; é **mudar o papel de cada peça**. Claims devem virar o eixo investigativo. Relevância de tema deve virar continuidade, não bloqueio. Estado do NPC deve modular o jeito de falar, não transformar todo turno em recusa.    

## 1. Trocar “modo de resposta” por “faixa de resposta”

Hoje o sistema decide um `ResponseMode` discreto e o prompt transforma isso em ordens fortes como “aja de forma evasiva”, “negue veementemente” ou “seja cauteloso”. O impacto disso é previsível: o modelo escolhe a forma mais segura e mais barata de obedecer, que é responder pouco, repetir recusa e secar o diálogo. Isso explica o seu teste com a Marina.  

Se você substituir isso por uma **faixa comportamental**, o resultado melhora muito. Em vez de “deny”, você passa algo como: “responda parcialmente, minimize responsabilidade, preserve o álibi, mostre irritação contida”. Em vez de “evasive”, algo como: “desvie do centro, mas entregue detalhe lateral e mantenha a conversa viva”.

A consequência positiva é alta: a fala fica mais natural, porque a IA não recebe uma ordem binária; recebe um papel dramático. A consequência negativa é que a LLM ganha mais liberdade de formulação, então o risco de escorregar para informação indevida sobe um pouco. A mitigação é simples: liberdade de **forma**, não de **conteúdo**. Ou seja, a faixa comportamental vem junto de uma lista curta do que é admissível agora e do que é proibido agora. O ganho de naturalidade é muito maior que o risco, desde que a política de conteúdo continue fechada pelo backend.  

## 2. Tornar o tópico ativo um contexto de continuidade, não um teste lexical

Seu código já aponta para isso. Há sinais de `active_topic_id`, `context_inherited`, `recent_topic_ids` e uma classificação de `continue_flow` quando a mensagem não detecta tópico novo, mas segue o fio anterior. Em uma versão mais recente, `last_topic_id` também é persistido no estado do suspeito. Isso está muito alinhado com o que você quer.   

A consequência positiva é enorme: o jogador pode perguntar “e depois?”, “mas isso não bate”, “e o relatório?” sem precisar repetir o alias perfeito. A conversa ganha memória curta e deixa de parecer uma sequência de prompts soltos. Isso também melhora muito o uso de evidência, porque ela pode herdar o tópico do turno anterior em vez de depender só da frase atual.  

A consequência negativa é o risco de “carregar tópico errado” por tempo demais. Exemplo: o jogador muda de assunto de forma implícita e o sistema acha que ainda está em `alibi`. Isso gera respostas coerentes demais com o tema antigo e incoerentes com a intenção nova. A mitigação ideal é TTL curto: tópico ativo vale por 1–2 turnos, cai se a nova mensagem trouxer outro tópico forte ou se houver alta novidade sem continuidade semântica. Para o seu objetivo, esse ajuste é praticamente obrigatório.

## 3. Relevância de tema deve parar de bloquear a fala e passar a modular o efeito mecânico

Hoje a arquitetura ainda favorece o raciocínio “tema certo no turno certo” para liberar conhecimento e evitar `out_of_context`. O próprio `get_allowed_knowledge_facts` só avalia itens cujo `topic_id` esteja em `detected_topics`, e as versões anteriores do sistema já mostravam o risco de parecer que o jogador está brigando com o parser.   

A mudança certa aqui não é abolir relevância. É mudar sua função.

Tema relevante deve influenciar:

* profundidade do que pode ser dito;
* chance de quebrar claim;
* intensidade da reação;
* efeito real da evidência.

Mas **não** deve impedir o NPC de responder de forma humana. Mesmo fora de contexto, ele pode reagir, minimizar, desviar, perguntar “por que está falando disso agora?”, ou dar detalhe lateral. A consequência positiva é que a conversa deixa de travar. A consequência negativa é que o jogador pode sentir que qualquer coisa “serve”. Para evitar isso, separe duas camadas: a camada verbal pode sempre responder; a camada mecânica só progride forte quando há relevância real. Assim você não mata a fluidez nem dissolve a estrutura investigativa.  

## 4. “Microavanço obrigatório” melhora muito a conversa, mas precisa de orçamento narrativo

Essa é uma das soluções mais fortes e também uma das mais perigosas.

A ideia é: toda resposta deve avançar algo. Não necessariamente um fato incriminador. Pode ser uma emoção, uma correção, uma minimização, um detalhe periférico, uma opinião sobre outro suspeito, uma mudança de tom. Isso resolve diretamente o problema do diálogo morto. 

O impacto positivo é muito alto. O jogador passa a sentir continuidade mesmo quando não arrancou confissão. O risco é óbvio: se você tornar “avanço” obrigatório sem controle, a IA vai vazar mais do que deveria e a progressão ficará rápida demais.

A solução é tratar avanço como orçamento por tipo:

* avanço factual;
* avanço emocional;
* avanço relacional;
* avanço contraditório;
* avanço atmosférico.

Só o primeiro gasta conteúdo sensível. Os outros mantêm a conversa viva sem abrir o cofre. Para o seu objetivo, eu adotaria isso. Sem esse princípio, o sistema tende a continuar caindo em recusa genérica.

## 5. Claims devem virar o centro da conversa, não só um evento especial

Hoje o sistema já possui claims, `resolve_broken_claims`, `broken_claims` no `suspect_state`, `claim_pressure_summary` no `render_context` e modos como `contradiction_repair`. Isso é a parte mais promissora do motor.    

A consequência positiva de recentrar o sistema em claims é que a conversa fica natural por um motivo estrutural: pessoas tentando sustentar uma versão não falam como “árvores de decisão de segredo”; elas falam como quem protege, ajusta, corrige e remenda afirmações anteriores. Isso produz fala humana quase automaticamente.

A consequência negativa é de autoria e tuning. Cada suspeito passa a exigir claims bem escritas, caminhos de quebra e respostas de reparo. Dá mais trabalho de conteúdo do que o modelo puro de `secret by evidence`. Mas o ganho em fantasia investigativa é enorme. Para o seu objetivo, essa é a solução com maior retorno estrutural.

Minha leitura: segredos devem virar consequência de claim quebrada ou pressão temática acumulada, não o eixo soberano do turno.

## 6. O estado do NPC deve modular estilo e profundidade, não ligar/desligar conversa

O seu sistema já atualiza `pressure`, `patience`, `stance`, `times_touched`, `sensitive_heat` e usa isso tanto na transição quanto na política de camadas de conhecimento. Isso é bom, mas o risco é usar estado como cancela rígida.  

Se você tratar o estado como modulador de estilo, o resultado melhora:

* pressão alta: frases mais curtas, mais defensivas, mais reparos;
* paciência baixa: menos detalhe, mais irritação, mais tentativa de encerrar;
* cooperação maior: mais precisão, mais memória, menos rodeio;
* calor em tópico sensível: mais hesitação, mais emoção, menos negação limpa.

A consequência positiva é naturalidade alta sem perder sistema. A consequência negativa é que o jogador pode sentir menos “feedback mecânico claro”, porque o efeito vira mais orgânico. Eu considero isso aceitável no seu caso, porque seu foco declarado é conversa natural, não legibilidade sistêmica máxima.

## 7. Separar “o que pode ser dito” de “o que deve aparecer” é essencial para evitar vazamento

Seu `render_context` já tem `allowed_facts`, `allowed_knowledge`, `new_knowledge_this_turn`, `must_not_reveal` e `forbidden_topics`. O problema é que o `prompt_builder` usa principalmente `npc_context["revealed_knowledge"]` como memória persistida, injeta conteúdo mandatório só quando há `new_knowledge_this_turn`, e o resto fica muito dependente do modo de resposta. Em outras palavras: o sistema já tem os campos certos, mas ainda não os usa para formar uma política fina de fala.   

Aqui eu faria uma separação dura:

* `admissible_now`: coisas que ela pode afirmar claramente;
* `hintable_now`: coisas que ela pode insinuar, mas não afirmar;
* `must_include_one_of`: pelo menos um microavanço precisa sair daqui;
* `must_not_reveal`: nunca pode sair;
* `preferred_deflections`: rotas de fuga desta personagem neste tema.

A consequência positiva é dupla: melhora naturalidade e reduz vazamento. A consequência negativa é mais trabalho no builder, porque você passa a curar o contexto de fala, não só despejar fatos já liberados. Mas esse é exatamente o tipo de custo que vale pagar no seu problema.

## 8. Mais histórico ajuda, mas só se for o histórico certo

Você disse que não quer medo de tokens agora. Isso muda bastante a recomendação.

Hoje o prompt builder já tem `_select_history`, com ideia de pinning de mensagens efetivas, mas a tendência do sistema ainda é usar o histórico mais como registro do que como “memória dramaturgicamente relevante”.  

A consequência positiva de ampliar histórico é melhor continuidade, menos repetição e mais referência a compromissos anteriores. A consequência negativa é poluição: histórico grande demais, sem curadoria, faz o modelo se apoiar no que é mais saliente, não no que é mais importante. Isso pode aumentar repetições e até vazamentos por associação indevida.

A melhor estratégia não é “mandar tudo”. É mandar:

* últimas 6–10 falas do diálogo;
* todas as falas pinned que quebraram claim ou produziram efeito forte;
* resumo curto de admissões já feitas;
* tópico ativo;
* claims quebradas;
* objetivo dramático do turno.

Como você não está apertado por token, isso fica confortável.

## 9. Evidência deve poder produzir fala sem necessariamente produzir unlock

Esse é um ajuste muito importante para o resultado percebido.

Se a evidência só é interessante quando revela `secret` ou quebra claim, o resto dos usos fica com cara de “sem efeito”. Se, ao contrário, toda evidência pode gerar resposta humana, mas só algumas geram avanço mecânico forte, a conversa fica mais viva e o sistema continua seguro. O seu próprio fluxo de evidência já distingue `evidence_effect`, `was_effective` e quebra de claims em versões mais novas.  

A consequência positiva é enorme para naturalidade. A negativa é que o jogador pode interpretar “reagiu à evidência” como “essa evidência é válida”, mesmo quando não era mecanicamente decisiva. Isso se resolve no texto: reação verbal não precisa significar confirmação factual. Pode ser só incômodo, tentativa de reinterpretar, ou ataque à credibilidade da prova.

## 10. O maior risco das mudanças é acelerar demais a revelação; o maior erro seria reagir a isso voltando para o travamento

Essa é a consequência sistêmica mais importante.

Quase todas as mudanças que melhoram naturalidade também aumentam a sensação de progresso. Se você não calibrar, a IA vai parecer boa porque “fala muito”, mas o caso ficará fácil demais. O jeito errado de compensar isso é voltar para recusa seca e gating lexical. O jeito certo é mover o freio para outro lugar:

* mais falas humanas;
* menos fatos nucleares por turno;
* mais reparos de claim;
* mais detalhe periférico;
* mais avanço emocional do que factual;
* revelação factual profunda só quando tópico + pressão + claim + evidência se alinham.

Assim você preserva fluxo e segura spoiler.

## O que eu adotaria no seu lugar

Eu não tentaria uma revolução total. Eu faria uma reordenação.

Primeiro, manteria claims, relevância temática e estado do NPC como pilares. Segundo, mudaria o papel de cada um:

* **claims**: núcleo da verdade investigativa;
* **tema relevante**: direcionador de profundidade e efeito, não bloqueio verbal;
* **estado do NPC**: modulador de tom, abertura e agressividade, não chave liga/desliga.

Em termos práticos, a melhor combinação para o seu objetivo é esta:

1. substituir `ResponseMode` rígido por “faixa de resposta” + `turn_goal`;
2. ativar de verdade o `active_topic_id/context_inherited` por 1–2 turnos;
3. garantir microavanço obrigatório por turno, mas com orçamento de avanço;
4. passar à IA um contexto curado em cinco blocos: admissível, insinuável, proibido, memória relevante, objetivo dramático;
5. fazer claims conduzirem as grandes rachaduras narrativas.

Essa combinação te dá a maior naturalidade com o menor risco de vazamento desnecessário, e aproveita exatamente as peças que o projeto já tem.    

Minha conclusão direta é:

O sistema atual trava porque usa o backend para controlar **a frase**. O backend deveria controlar **a informação** e deixar a IA escolher a frase dentro de um trilho comportamental. Quando você faz essa troca, a conversa fica natural sem perder soberania.

No próximo passo, eu posso transformar isso em uma proposta concreta de `render_context v2` e `build_npc_prompt v2`, já com campos, heurísticas e exemplos de saída para a Marina.
