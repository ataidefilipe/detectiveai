Abaixo está a matriz operacional de UX do interrogatório, pensada para transformar a análise em regra de jogo utilizável.

Ela parte de quatro princípios:

1. **o jogador pode falar naturalmente**;
2. **o backend interpreta e decide**;
3. **a IA apenas encena a resposta**;
4. **o progresso investigativo precisa parecer humano, não mecânico**. 

---

# Matriz: fala do jogador × efeito sistêmico × resposta ideal × risco de frustração

## 1. Pergunta aberta de exploração

**Exemplos**

* “Quero ouvir sua versão desde o começo.”
* “Como era sua relação com a vítima?”
* “O que aconteceu naquela noite?”

**Leitura do backend**

* `intent`: `ask`
* `specificity`: baixa ou média
* tenta detectar tópico principal
* pouco ou nenhum aumento de pressão
* baixo risco de perda de paciência
* pode abrir `last_topic_id` para os próximos turnos.

**Impacto ideal nas variáveis**

* `pressure`: +0 a +5
* `patience`: 0
* `rapport`: +0 a +5
* `topic_touch_count`: +1 no tópico detectado
* `stance`: tende a permanecer neutra

**Resposta ideal do NPC**

* versão superficial
* fala coerente com personalidade
* pequena pista emocional
* sem entrega de informação crítica cedo demais

**Sinal que o jogador deve perceber**

* “esse assunto existe”
* “essa pessoa tem uma versão pronta”
* “há espaço para aprofundar”

**Risco de frustração**

* alto se a pergunta natural não mapear tópico nenhum
* o jogador sente que falou algo válido e recebeu resposta genérica

**Mitigação**

* se não houver tópico claro, usar contexto recente ou classificar como “continuação neutra”
* nunca punir esse tipo de fala logo no início

---

## 2. Pergunta específica de detalhe

**Exemplos**

* “Quem viu você sair?”
* “Você falou 22h. Tem certeza desse horário?”
* “Em que momento você encontrou a vítima?”

**Leitura do backend**

* `intent`: `ask`
* `specificity`: média ou alta
* forte chance de detectar tópico
* deve aumentar compromisso narrativo do suspeito.

**Impacto ideal nas variáveis**

* `pressure`: +5 a +10
* `patience`: 0
* `rapport`: +0 a +3
* `topic_touch_count`: +1
* chance de promover `conversation_effect` para algo como `deeper_topic`

**Resposta ideal do NPC**

* mais concreta
* menos ampla
* produz material investigável
* pode introduzir um `claim` implícito

**Sinal para o jogador**

* “agora ele se comprometeu com uma versão”
* “isso posso testar depois”

**Risco de frustração**

* baixo, se o tópico for reconhecido
* médio, se o sistema responder como se fosse pergunta genérica

**Mitigação**

* perguntas com numerais, nomes, ordem temporal e pessoas devem ganhar peso maior de especificidade
* esse tipo de fala deve ser o principal combustível do jogo

---

## 3. Reabordagem / reformulação honesta

**Exemplos**

* “Deixa eu perguntar de outro jeito.”
* “Não é onde você estava, é quem pode confirmar isso.”
* “Então o ponto não é o jantar, é o horário.”

**Leitura do backend**

* pode parecer repetição lexical ou semântica
* deveria ser classificada como `reframe`, não `repeat`, quando houver mudança de foco real.

**Impacto ideal nas variáveis**

* `pressure`: +0 a +8
* `patience`: 0 ou -2
* `rapport`: +0
* mantém tópico ativo ou troca para subtópico
* não deve disparar penalidade cedo

**Resposta ideal do NPC**

* nota a mudança de ângulo
* responde ajustando a defesa
* às vezes revela uma inconsistência menor

**Sinal para o jogador**

* “reformular funciona”
* “posso insistir com inteligência sem parecer spam”

**Risco de frustração**

* muito alto se o sistema ler como repetição burra

**Mitigação**

* só penalizar repetição depois de 2 ou 3 reabordagens sem ganho semântico
* usar `last_topic_id` e palavras de transição como “então”, “ou seja”, “de outro jeito” para favorecer `reframe`.

---

## 4. Pressão direta

**Exemplos**

* “Você está mentindo.”
* “Sua história não fecha.”
* “Você omitiu alguma coisa.”

**Leitura do backend**

* `intent`: `pressure` ou `accuse`
* aumenta `pressure`
* se tocar tópico sensível, também reduz `patience`
* tende a empurrar `stance` para defensivo, pressionado ou irritado.

**Impacto ideal nas variáveis**

* `pressure`: +10 a +20
* `patience`: -5 a -10
* `rapport`: -3 a -8
* `stance`: defensivo / pressionado

**Resposta ideal do NPC**

* reação mais forte
* fala mais curta ou agressiva
* pode negar de forma mais específica
* raramente deveria revelar algo importante sozinha

**Sinal para o jogador**

* “acertei um nervo”
* “ele está afetado”
* “posso quebrá-lo, mas posso também fechar a conversa”

**Risco de frustração**

* médio se toda pressão só piorar a conversa sem benefício
* médio se pressão sempre for a melhor estratégia

**Mitigação**

* alguns suspeitos devem reagir mal à pressão, outros devem escorregar sob pressão
* pressão precisa ter payoff situacional, não universal

---

## 5. Empatia / acalmar / aproximação

**Exemplos**

* “Não estou aqui para te condenar.”
* “Quero entender antes de concluir qualquer coisa.”
* “Se você estiver escondendo algo por medo, essa é a hora de falar.”

**Leitura do backend**

* `intent`: `calm`
* reduz pressão
* aumenta `rapport`
* pode destravar conhecimento contextual, não necessariamente prova.

**Impacto ideal nas variáveis**

* `pressure`: -5
* `patience`: +0 a +5
* `rapport`: +5 a +12
* `stance`: neutra ou cooperativa

**Resposta ideal do NPC**

* mais detalhada
* menos hostil
* admite emoções, não necessariamente culpa
* entrega contexto, laços, medos, motivos indiretos

**Sinal para o jogador**

* “essa pessoa responde melhor quando eu reduzo a tensão”
* “nem tudo se resolve no ataque”

**Risco de frustração**

* baixo, desde que haja retorno tangível
* alto se “ser gentil” nunca for útil

**Mitigação**

* rapport alto deve alterar qualidade do material verbalizado
* não revelar solução, mas sim contexto que apoia dedução

---

## 6. Confronto com evidência bem contextualizado

**Exemplos**

* “Você disse que não esteve no bar. Então por que sua digital está nessa taça?”
* “Se você saiu cedo, explica a câmera do estacionamento.”
* “Você nega o encontro, mas sua mensagem mostra o contrário.”

**Leitura do backend**

* `intent`: `confront`
* tópico atual ou recente deve pesar fortemente
* avalia `evidence_effect`: `revealed_secret`, `reaction_only`, `duplicate`, `out_of_context`
* pode quebrar mentira ou liberar conhecimento novo. 

**Impacto ideal nas variáveis**

* `pressure`: +15 a +25
* `patience`: -5
* `rapport`: varia pouco
* `stance`: pressionado / defensivo
* chance alta de evento estrutural: segredo, claim quebrado, recuo, mudança de versão

**Resposta ideal do NPC**

* forte mudança de tom
* desvio menos confortável
* meia admissão, justificativa ou recuo
* se o confronto for perfeito, uma quebra real

**Sinal para o jogador**

* “acertei em cheio”
* “essa prova encaixou”
* “a versão dele rachou”

**Risco de frustração**

* altíssimo se o jogador contextualiza bem, mas o sistema responde `out_of_context`
* isso destrói a confiança no motor

**Mitigação**

* usar não só a frase atual, mas `last_topic_id` e talvez uma janela dos 2 últimos turnos
* esse tipo de jogada precisa ser confiável

---

## 7. Evidência jogada sem contexto

**Exemplos**

* falar algo solto e anexar prova sem ponte verbal
* testar várias evidências em sequência

**Leitura do backend**

* chance de `out_of_context` ou `reaction_only`
* pequena penalidade
* mantém risco de exploração por tentativa e erro. 

**Impacto ideal nas variáveis**

* `pressure`: +5
* `patience`: -2 a -5
* `rapport`: -2
* sem revelação forte

**Resposta ideal do NPC**

* reação contida
* pode demonstrar desconforto, mas sem avanço concreto
* reforça que a evidência foi mal usada

**Sinal para o jogador**

* “a prova importa, mas o momento e o contexto também”

**Risco de frustração**

* baixo, desde que a diferença para o bom confronto seja clara

**Mitigação**

* mostrar isso mais pela fala do NPC do que por mensagem técnica
* ex.: “isso não prova o que você acha que prova”

---

## 8. Acusação prematura durante o interrogatório

**Exemplos**

* “Foi você.”
* “Você matou a vítima.”
* “Seu motivo era dinheiro, não era?”

**Leitura do backend**

* `intent`: `accuse`
* alto impacto emocional
* deveria subir pressão e reduzir paciência, mas nem sempre render avanço real.

**Impacto ideal nas variáveis**

* `pressure`: +15
* `patience`: -10
* `rapport`: -8
* `stance`: irritado ou defensivo

**Resposta ideal do NPC**

* negação forte
* tentativa de inverter culpa
* só funciona bem se já houver base factual

**Sinal para o jogador**

* “acusar cedo sem montar o caso é arriscado”

**Risco de frustração**

* baixo, porque a lógica é intuitiva
* médio se nunca for útil mesmo quando o jogador construiu o terreno

**Mitigação**

* se houver claims já pressionados e prova forte recente, a acusação pode provocar escorregão verbal

---

## 9. Conversa oblíqua, humana, indireta

**Exemplos**

* “Toda vez que eu menciono esse nome você muda de tom.”
* “Você está mais preocupado com o horário ou com quem estava lá?”
* “Curioso como você nega antes mesmo de eu terminar a pergunta.”

**Leitura do backend**

* esse é o caso mais difícil
* semanticamente forte para humano
* lexicalmente fraco para um parser simples.

**Impacto ideal nas variáveis**

* `pressure`: +5 a +12
* `patience`: 0 ou -2
* `rapport`: varia
* deveria herdar `last_topic_id` ou virar leitura meta de comportamento

**Resposta ideal do NPC**

* reação emocional
* pequena fissura de postura
* sem exigir keyword exata

**Sinal para o jogador**

* “o jogo entende comportamento conversacional, não só substantivos”

**Risco de frustração**

* máximo, se o sistema ignorar completamente

**Mitigação**

* usar contexto recente
* criar uma classe de leitura “meta-confronto” baseada em padrões como “você hesitou”, “mudou de tom”, “nega cedo”
* isso não exige IA decidir nada; é só regra

---

## 10. Jogador perdido / fala vaga / tentativa de manter conversa viva

**Exemplos**

* “Certo… continua.”
* “Entendi. E depois?”
* “Tá, me fala mais.”

**Leitura do backend**

* pouca informação semântica nova
* não deveria punir muito
* deveria manter tópico atual, não resetar.

**Impacto ideal nas variáveis**

* `pressure`: 0
* `patience`: 0
* `rapport`: 0 a +2
* mantém foco conversacional

**Resposta ideal do NPC**

* continua linha atual
* adiciona detalhe incremental
* às vezes repete com nuance

**Sinal para o jogador**

* “posso deixar o NPC continuar”
* “o fluxo não quebra quando eu não tenho uma pergunta perfeita”

**Risco de frustração**

* médio se a conversa colapsar em respostas genéricas

**Mitigação**

* em turnos desse tipo, usar fortemente `last_topic_id` e memória curta

---

# Matriz resumida de design

| Tipo de fala              |     Pressão |   Paciência |    Rapport | Melhor uso                   | Maior risco                |
| ------------------------- | ----------: | ----------: | ---------: | ---------------------------- | -------------------------- |
| Pergunta aberta           |       baixa |      neutro |  leve alta | exploração                   | parecer genérica           |
| Pergunta específica       |       média |      neutro |  leve alta | criar compromisso            | sistema tratar como banal  |
| Reformulação              | baixa/média |  leve queda |     neutro | aprofundar sem spam          | virar repetição injusta    |
| Pressão direta            |        alta |       queda |      queda | testar nervo / forçar reação | virar estratégia dominante |
| Empatia                   |       baixa | neutro/alta |       alta | destravar contexto           | não ter payoff             |
| Evidência contextual      |  muito alta |  leve queda |     neutro | quebrar versão               | `out_of_context` injusto   |
| Evidência sem contexto    | baixa/média |  leve queda | leve queda | teste bruto                  | estimular spam             |
| Acusação prematura        |        alta |  queda alta | queda alta | provocar reação final        | punir cedo demais          |
| Fala oblíqua humana       |       média |      neutro |      varia | leitura refinada             | parser falhar              |
| Fala vaga de continuidade |      neutro |      neutro |  leve alta | manter fluxo                 | resposta morta             |

---

# Regras práticas para o backend preservar naturalidade

## Regra A — contexto curto obrigatório

Toda interpretação deve olhar:

* turno atual,
* `last_topic_id`,
* últimos 1 ou 2 turnos resumidos.

Sem isso, conversa natural quebra.

## Regra B — repetir não é o mesmo que insistir

O backend precisa distinguir:

* repetição vazia,
* reformulação,
* aprofundamento,
* confronto.

Hoje já existe `novelty`, mas ela precisa ser calibrada em favor do humano.

## Regra C — evidência boa depende de momento, não de keyword perfeita

Se o jogador vem de dois turnos sobre “álibi” e usa a prova do estacionamento, isso deve encaixar mesmo sem repetir o nome do tópico naquele exato turno. 

## Regra D — rapport e pressure precisam produzir estilos diferentes de avanço

Não basta alterar número.
Eles precisam mudar o tipo de material que sai:

* `rapport`: contexto, vulnerabilidade, justificativas;
* `pressure`: negação específica, fissura, irritação, escorregão.

## Regra E — a IA não decide, mas precisa soar como se a pessoa decidisse

O backend entrega o modo.
A IA entrega a superfície dramática. Isso já está bem encaminhado pelo `NpcResponseRenderContext`. 

---

# Modelo ideal de resposta do NPC por estado

## Neutro

* responde normalmente
* protege segredos
* aceita explorar temas

## Defensivo

* responde, mas limita
* nega mais
* tenta encurtar

## Pressionado

* comete pequenas inconsistências
* corrige a si mesmo
* reage forte à prova

## Cooperativo

* detalha mais
* oferece contexto
* admite desconfortos laterais

## Irritado

* corta assunto
* ataca o investigador
* arrisca encerrar conversa

Isso conversa diretamente com os shifts e estados já previstos no sistema.

---

# O que implementar primeiro

## P0

Adicionar uma tabela mental simples ao motor:

**entrada do jogador**
→ intenção
→ tópico atual ou herdado
→ tipo de jogada
→ delta em pressão/paciência/rapport
→ resultado estrutural
→ modo de resposta do NPC

## P0

Formalizar `claim` por suspeito:

* “saí às 22h”
* “não estive no bar”
* “não conhecia a vítima direito”

Depois:

* claim confirmado,
* claim sob suspeita,
* claim quebrado.

Isso é o que transforma conversa em investigação.

## P0

Tolerância alta para reformulação nos primeiros turnos do mesmo tópico.

## P1

Perfis comportamentais de suspeito:

* reage mal à pressão,
* reage bem à empatia,
* mente melhor sob calma,
* se contradiz sob confronto.

## P1

Feedback menos técnico no frontend.
Mais pista emocional na fala, menos etiqueta sistêmica.

---

# Conclusão operacional

A matriz acima define o que o jogador faz, o que o sistema entende, como as variáveis mudam e qual sensação final ele deve ter.

O objetivo correto não é “entender linguagem natural perfeitamente”.
O objetivo correto é:

**entender o suficiente para que o jogador sinta continuidade, coerência e consequência nas suas escolhas de conversa.**

E isso pode ser feito sem dar nenhum poder de decisão à IA, desde que o backend assuma três responsabilidades:

* memória curta de contexto;
* registro de claims e contradições;
* transições de estado que alterem não só números, mas o tipo de informação verbalizada.
