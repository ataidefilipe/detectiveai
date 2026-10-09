## Veredito geral

**A Sessão 4 melhorou a estrutura investigativa, mas ainda não sustenta uma conversa natural de ponta a ponta.** Marina agora consegue defender uma versão e recuar diante de uma prova. Porém, alterna entre dois extremos:

- **Perguntas cotidianas:** responde como um sistema sem dados suficientes.
- **Evidências e assuntos centrais:** oferece mais informação do que a pergunta exigia, às vezes antecipando etapas da investigação.

Portanto, a resposta à pergunta principal é: **há uma combinação de limitações de contexto, problemas de condução técnica e insuficiência de detalhamento narrativo disponível na conversa. Não é simplesmente uma personagem escolhendo se defender.**

O núcleo dramático tem potencial. O problema está em fazer esse núcleo funcionar entre os grandes eventos de quebra de mentira.

### Limite desta avaliação

O contexto contém documentação, transcrição e recortes de telemetria, mas **não o conteúdo efetivo de `piloto.json` nem a implementação dos serviços**. Assim:

- É possível avaliar com segurança o resultado percebido pelo jogador.
- É possível apontar hipóteses técnicas bem fundamentadas.
- Não é possível afirmar, em todos os casos, se determinado fato estava ausente do cenário, bloqueado pela política ou disponível e ignorado pela geração.

Também há uma distinção importante: **`Provider=heuristic` indica o provedor de análise da mensagem, não necessariamente o gerador da fala.** Para identificar geração por OpenAI, fallback ou intervenção do guard, seriam necessários os campos `ai.adapter`, `guard_blocked` e o prompt completo.

---

## 1. Qualidade das informações e naturalidade dramática

### O que funcionou

#### A defesa do álibi criou um compromisso investigável

Os turnos 4 e 5 cumprem uma função essencial:

> “Sim, fiquei sozinha no meu quarto a noite toda. Não saí em nenhum momento, nem para jantar.”

Agora existe uma afirmação inequívoca que o jogador pode testar. A sequência **perguntar → confirmar → confrontar** funciona.

Esse é o ganho mais evidente da injeção de `active_claims`: Marina deixa de ser apenas uma fonte bloqueada de segredos e passa a sustentar uma versão.

#### A evidência foi reconhecida como objeto concreto

No turno 6, Marina responde ao registro do cartão, inclusive ao horário de 22h14. Não pergunta o que é a prova nem expõe diretamente o funcionamento do jogo.

O turno 11 também oferece um recuo compreensível diante do relatório.

**As melhorias de contexto material e de sustentação de claims aparecem no resultado.**

#### Há momentos de atuação apropriada

Alguns trechos expressam bem a tentativa de diminuir a própria responsabilidade:

- “Fiz algumas alterações [...] só algumas.”
- “Eu precisava do emprego.”
- “O esquema era dos dois.”

São falas com função defensiva: minimizar participação, justificar comportamento e dividir responsabilidade. Isso combina melhor com Marina do que recusas genéricas.

### O que ainda não funcionou

#### A abertura parece uma limitação de conhecimento do assistente

No turno 2:

> “Não quero inventar uma cronologia do meu dia.”

E no turno 10:

> “Sem correr o risco de afirmar algo que não sei.”

Essas frases poderiam existir isoladamente numa conversa humana. Mas, neste contexto, soam como **a política antialucinação aparecendo na voz da personagem**.

Uma assistente financeira pode não lembrar todos os horários ou desconhecer a origem de uma irregularidade. O que enfraquece a cena é ela não conseguir oferecer praticamente nenhum recorte concreto sobre o próprio dia ou sobre algo que acabou de afirmar ter observado.

**Preservar a verdade do cenário está correto. Transformar ausência de contexto em fala metacognitiva recorrente não está.**

#### O monólogo foi reduzido, não eliminado como problema de ritmo

O turno 6 ainda concentra:

1. Retratação do álibi.
2. Registro do cartão às 22h14.
3. Acesso ao andar.
4. Presença no escritório.
5. Discussão violenta.
6. Relação com o relatório.
7. “Ameaça de traição”.
8. Defesa da versão sobre autoria das inconsistências.

Isso não é um monólogo muito longo, mas é **uma descarga de informações e de linhas investigativas**.

O jogador apresentou uma prova contra a permanência no quarto. A resposta já entrega presença, conflito e elementos de motivação.

O turno 11 repete o padrão em escala menor: admite alterações, inclui revisão de rotina, repara a mentira e apresenta ameaça de denúncia e esquema compartilhado.

**Limitar `must_say` a dois itens não limita o número total de revelações.** O conteúdo de `may_say` continua disponível, e um único item pode conter várias proposições relevantes.

#### Uma parte do pingue-pongue foi consumida corrigindo a própria resposta

O turno 3 existe porque a resposta anterior não respondeu à pergunta.

O turno 7 existe porque “ameaça de traição” introduziu uma ambiguidade que Marina precisou corrigir.

Essas trocas movimentam a conversa, mas não necessariamente a investigação. Há diferença entre:

- O jogador explorar uma ambiguidade deliberada da suspeita.
- O jogador reparar uma formulação imprecisa do sistema.

Aqui, o segundo caso é uma hipótese forte.

### Comparação com a Sessão 3

Considerando os problemas anteriores descritos, houve progresso real:

| Aspecto | Avaliação na Sessão 4 |
|---|---|
| Sustentar álibi | Melhorou claramente |
| Reconhecer evidência concreta | Melhorou claramente |
| Evitar grandes blocos expositivos | Melhorou parcialmente |
| Responder a perguntas abertas | Ainda fraco |
| Manter continuidade de detalhes | Ainda fraco |
| Preservar coerência entre admissões e claims | Precisa de auditoria |

**A experiência ficou mais funcional, mas ainda não considero a naturalidade satisfatória.** Os grandes eventos funcionam melhor do que os intervalos entre eles.

---

## 2. Marina está atuando corretamente?

### Parcialmente: há defesa, mas pouca diferenciação psicológica

O perfil descrito — nervosa, meticulosa e tentando parecer calma — deveria aparecer principalmente em:

- Escolha cuidadosa de palavras.
- Correções de escopo.
- Minimização.
- Tentativas de manter controle sobre a interpretação.
- Mudança de ritmo quando sua versão deixa de ser sustentável.

Não precisa significar reticências constantes, gagueira ou gestos em toda fala.

Na sessão, aparecem hesitação inicial e algumas justificativas. Entretanto, Marina permanece majoritariamente com uma voz explicativa e uniforme, inclusive depois da quebra do álibi.

No turno 6:

> “Tem razão — eu não fui sincera [...]”

É uma admissão clara, mas bastante organizada para um momento que deveria produzir uma rachadura perceptível no controle da personagem.

Uma alternativa de encenação, **usando apenas fatos já presentes naquele turno**, seria:

> “Eu fui ao escritório do Heitor, sim. Não fiquei no quarto a noite toda.”

Não é preciso acrescentar um motivo inventado para mentir nem revelar imediatamente a discussão. A própria economia da resposta pode demonstrar resistência.

### Diagnóstico das recusas

| Turno | O que está comprovado | Leitura mais provável |
|---|---|---|
| **2** | Sem tópico detectado; paciência em 50; resposta sem cronologia | Falha de encaminhamento temático e/ou insuficiência de fatos disponíveis. Não há evidência de bloqueio por paciência. |
| **3** | Continua sem tópico; recorre ao álibi | A versão oficial oferece uma saída, mas a pergunta sobre o dia continua sem resposta. |
| **4** | Tópico `alibi` reconhecido; paciência preservada | Falta uma justificativa disponível para a versão ou falta orientação de encenação. Detectar o tópico, sozinho, não resolve. |
| **10** | Sem tópico detectado; paciência 8; modo `neutral_answer` | Continuidade temática possivelmente falhou. Paciência baixa pode influenciar, mas não prova bloqueio do conteúdo. Também pode faltar detalhe contábil autorizado. |

**Não há base para classificar essas falas como uma defesa jurídica deliberada.** Marina não estabelece consistentemente um limite de depoimento; ela afirma não possuir material para responder.

### O classificador prejudicou a abertura?

**Sim, no resultado observado.**

“O que você fez ao longo do dia?” é uma pergunta natural e prevista pela proposta de UX. Não reconhecer seu vínculo com rotina ou cronologia reduz a chance de selecionar os conhecimentos apropriados.

Mas há duas ressalvas:

1. A pergunta mistura rotina e localização. Não existe necessariamente um único tópico correto para toda a mensagem.
2. `Tópico=None` não comprova ausência total de contexto no prompt: a resposta do turno 3 demonstra acesso ao álibi.

A correção não deve ser transformar “o que você fez” em um alias universal de rotina. Dependendo do contexto, a mesma frase pode perguntar sobre o relatório, a discussão ou o crime.

**É necessário combinar reconhecimento lexical com continuidade conversacional.**

### O turno 9 apresenta uma incoerência mais importante que a secura inicial

Marina diz:

> “Não sei quem as fez.”

E, na mesma resposta:

> “Fiz algumas alterações que ele pediu.”

Isso pode ser coerente **se o cenário distinguir alterações legítimas de adulterações ou inconsistências específicas**. A fala, contudo, não estabelece essa diferença.

Para o jogador, ela parece admitir participação antes da prova e depois voltar à negação no turno 10. No turno 11, reconhece que a negação era inadequada.

Há três possibilidades a verificar:

- Os fatos liberados já conflitam com a claim ativa.
- A geração ampliou indevidamente uma informação permitida.
- A distinção existe no cenário, mas ficou ambígua na verbalização.

O modo `deny` junto de uma admissão não é, por si só, errado: alguém pode negar homicídio e admitir fraude. **O problema é não ficar claro qual proposição está sendo negada.**

Isso merece prioridade porque ameaça a confiança do jogador na lógica das contradições.

---

## 3. O cenário dá espaço suficiente?

### Existe um núcleo dramático suficiente

O material apresentado contém:

- Álibi falso.
- Registro de acesso.
- Conflito com a vítima.
- Pressão profissional.
- Alterações em relatório.
- Ameaças e responsabilidade compartilhada.

Isso é suficiente para uma boa cena central de interrogatório. **Não falta conflito.**

O que a sessão sugere é falta de profundidade utilizável ao redor desse núcleo.

### Cargo não equivale a rotina; rotina não equivale ao dia investigado

Responder “sou assistente financeira há cinco anos” informa identidade profissional, não atividades do dia.

São três necessidades diferentes:

1. **Função:** o que Marina faz normalmente.
2. **Rotina:** como costuma trabalhar.
3. **Cronologia:** o que fez naquela data.

Adicionar `rotina_trabalho` resolve apenas parte desse espaço. Mesmo com classificação perfeita, o sistema continuará limitado se só houver informações profissionais genéricas.

O mesmo vale para o relatório:

> “Havia inconsistências.”

Essa informação cria naturalmente as perguntas:

- Que inconsistências?
- Como você percebeu?
- O que deveria estar correto?
- Qual era sua responsabilidade naquele documento?

Se não existem respostas autoradas e graduadas para isso, o jogador encontra uma pista que não suporta aprofundamento.

### A melhor expansão é pequena e investigável

Eu não aumentaria a biografia inteira. Acrescentaria respostas canônicas às perguntas imediatamente provocadas pelos fatos existentes:

| Informação existente | Detalhamento necessário |
|---|---|
| Assistente financeira | Responsabilidades concretas e limites de acesso |
| Relatório em revisão | Processo de revisão e participação de Marina |
| Inconsistências | Natureza observável do problema, sem antecipar autoria |
| Ficou no quarto | Versão oficial minimamente sustentável, caso essa explicação seja importante |
| Discussão com Heitor | Separação clara entre cobrança, ameaça e motivo do confronto |
| Outros suspeitos | Conhecimento de Marina sobre eles, com origem e confiabilidade |

Esses detalhes precisam ser escritos e validados contra a cronologia. **Não devem ser improvisados pelo LLM.**

Os `flavor_slots` documentados servem para aspectos cosméticos consistentes. Não são um substituto seguro para horários, deslocamentos, acessos ou fatos que possam alterar uma hipótese criminal.

### E os outros ângulos?

A arquitetura e o schema comportam exploração lateral, inclusive com `kind` e `reliability`. Porém, esta sessão não testa conversas sobre os outros suspeitos, e o JSON não foi fornecido.

Portanto:

- **Há suporte estrutural para esses ângulos.**
- **Não há evidência suficiente de que o conteúdo atual os sustente bem.**

---

## 4. Um ponto técnico a verificar antes de alterar o cenário

### As mudanças no JSON chegaram ao banco de produção?

`docs/DEPLOYMENT.md` descreve o bootstrap como idempotente, **pulando registros existentes**.

Isso cria uma hipótese operacional relevante:

> Alterar `scenarios/piloto.json` e publicar a aplicação pode não atualizar automaticamente um cenário já persistido no PostgreSQL.

Não estou afirmando que isso aconteceu. Pode ter havido uma atualização explícita não descrita no contexto.

Mas, antes de concluir que `rotina_trabalho` é insuficiente ou que seus aliases falharam, é necessário verificar:

- O tópico existe no cenário persistido?
- Os aliases novos estão presentes?
- Os conhecimentos novos estão associados aos suspeitos?
- Esses dados chegaram ao contexto dos turnos 2 e 3?

**Sem essa verificação, corre-se o risco de ajustar conteúdo que a produção ainda não utiliza.** Se houver divergência, a solução deve ser uma atualização controlada dos dados, não apagar o banco ou as sessões.

---

## 5. Recomendações prioritárias e cirúrgicas

### P0 — Identificar em qual etapa a informação desaparece

Usar os traces existentes com `include_prompt=true`, especialmente nos turnos 2, 3, 6, 9, 10 e 11.

Para cada pergunta problemática, verificar:

1. O fato existe no cenário persistido?
2. Foi selecionado pelo tópico atual ou herdado?
3. A política autorizou sua exposição?
4. Entrou no contexto de renderização?
5. A geração o utilizou?
6. Houve fallback ou bloqueio pelo guard?

Essa sequência separa **problema de autoria, classificação, revelação e atuação** sem adivinhar a causa.

### P0 — Resolver coerência entre claims e fatos liberados

Auditar a relação entre a claim “não sei quem fez” e as camadas que permitem “fiz algumas alterações”.

A correção pode estar no texto autoral, na política de liberação ou na formulação da claim. Não recomendo criar imediatamente um novo mecanismo genérico.

Também revisar “ameaça de traição”, “ameaça de demissão” e “ameaça de denúncia”. Podem ser eventos diferentes; se forem, a progressão precisa distingui-los. Se não forem, há deriva de significado.

### P1 — Corrigir continuidade, não apenas adicionar aliases

Nos serviços existentes de contexto e classificação:

- Cobrir perguntas naturais sobre rotina e localização.
- Normalizar acentos e variações já identificadas nas auditorias.
- Fazer “que tipo de inconsistências?” continuar `relatorio_contabil`.
- Testar também a grafia digitada: “inconsitencias”.
- Dar precedência a uma mudança explícita de assunto.
- Evitar herdar automaticamente um tópico sensível para toda mensagem vaga.

Uma comparação controlada com o classificador semântico existente pode ajudar a localizar o gargalo. **Não substitui conteúdo autoral nem balanceamento.**

### P1 — Controlar a seleção de fatos, não só o tamanho de `must_say`

Preservaria o contrato atual e ajustaria a seleção no builder:

1. Priorizar fatos que respondem à pergunta ou reparam a claim quebrada.
2. Retirar do contexto de fala daquele turno os opcionais sem relevância imediata.
3. Evitar repetir claims não relacionadas ao confronto.
4. Revisar itens autorais que agrupam muitas revelações.

O conhecimento desbloqueado pode continuar persistido sem ser todo oferecido para verbalização imediata.

Também é necessário verificar a semântica do dossiê: **um fato marcado como descoberto, mas nunca verbalizado porque caiu em `may_say`, pode gerar divergência entre conversa e registro.**

### P1 — Afinar a atuação sem reescrever a arquitetura

No `prompt_builder` e nas diretivas já existentes:

- Responder primeiro à pergunta atual.
- Não verbalizar limitações de contexto ou instruções antialucinação.
- Sustentar apenas a claim relevante, sem recitá-la em toda resposta.
- Mostrar nervosismo por precisão defensiva, minimização e autocorreção.
- Não confundir linguagem contida com ausência de personalidade.
- Permitir avanço emocional sem exigir uma nova pista por turno.

Isso não deve virar licença para inventar justificativas, esquecimentos ou rotinas. **Se a pergunta previsível exige um fato ausente, a solução é autorar o fato.**

### P1 — Rever o custo de explorar tópicos sensíveis

Nos turnos 7, 8 e 9, a perda é sempre de 14 pontos de paciência, embora as ações sejam diferentes:

- Pedir esclarecimento sobre uma ameaça.
- Fazer uma acusação de agressão.
- Abrir uma pergunta sobre o relatório.

Essa uniformidade merece revisão à luz de `interrogatorio_ux.md`, que diferencia exploração, aprofundamento e acusação.

Além disso, o cartão no turno 6 quebra a versão sem alterar pressão ou postura. Isso não prova erro — pode haver compensações —, mas merece inspecionar os deltas componentes.

**Corrigir o reconhecimento do turno 10 sem revisar as penalidades pode piorar a experiência:** uma pergunta legítima de detalhe passaria a ser reconhecida como sensível e poderia consumir a paciência restante.

No turno 11 ela chega a zero. A documentação prevê fechamento, mas a telemetria fornecida não informa `is_closed`. É preciso verificar o resultado efetivo antes de afirmar que a conversa terminou.

---

## 6. Critérios de sucesso para a próxima sessão

Eu repetiria esta conversa como regressão, adicionando uma ramificação empática e outra sobre um suspeito diferente.

Consideraria a melhoria demonstrada se:

- A pergunta sobre o dia receber um recorte autorado, não uma explicação sobre “não inventar”.
- O detalhe sobre inconsistências preservar o tópico, inclusive com erro de digitação.
- O cartão produzir uma retratação proporcional, sem descarregar automaticamente conflito e motivação.
- Não houver negação e admissão incompatíveis sobre a mesma proposição.
- Uma pergunta calma de aprofundamento tiver tratamento distinto de uma acusação.
- A voz de Marina mudar perceptivelmente após a quebra da versão, sem precisar de novo fato.
- Nenhum detalhe ausente for inventado para tornar a fala mais fluida.
- Fatos da conversa, claims e dossiê permanecerem alinhados.

## Conclusão

**Marina tem material para atuar, mas a sessão ainda não lhe entrega esse material com a granularidade, a continuidade e a seleção necessárias.**

O álibi e as evidências melhoraram. Os principais problemas restantes são:

1. **Continuidade temática frágil.**
2. **Pouco detalhe utilizável nas perguntas periféricas.**
3. **Admissões e claims potencialmente incompatíveis.**
4. **Excesso de informação relevante nos confrontos.**
5. **Custo emocional pouco diferenciado entre explorar e acusar.**

Eu não começaria por um `render_context v2`, novos modos ou mais liberdade factual para o LLM. Começaria por **confirmar os dados em produção, auditar as admissões, corrigir a continuidade e selecionar melhor o conteúdo que já existe**. Depois, preencheria as poucas lacunas autorais que impedem respostas humanas.

**O objetivo não é fazer Marina falar mais: é fazer cada resposta parecer uma escolha da personagem, e não uma consequência visível da disponibilidade de dados.**