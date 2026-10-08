# Schema de Cenário — Detective AI

Referência completa do formato JSON usado para definir cenários do jogo.

---

## Estrutura Geral

```json
{
  "scenario_code": "string",
  "title": "string",
  "description": "string (opcional)",
  "case_summary": "string (opcional, interno)",
  "culprit": "suspect_id",
  "true_motive_key": "motive_key (opcional)",
  "required_broken_lie_ids": ["lie_id", ...],
  "suspects": [...],
  "evidences": [...],
  "secrets": [...],
  "topics": [...],
  "motives": [...]
}
```

---

## Campos

### `ScenarioConfig` (raiz)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `scenario_code` | string | ✅ | Código único estável. Usado para idempotência no loader. |
| `title` | string | ✅ | Título do cenário exibido ao jogador. |
| `description` | string | ❌ | Descrição curta do cenário. |
| `case_summary` | string | ❌ | Resumo interno do caso — não exposto ao jogador. |
| `culprit` | string | ✅ | `id` estável do suspeito culpado. Deve existir em `suspects`. |
| `true_motive_key` | string | ❌ | `key` da motivação verdadeira. Deve existir em `motives`. |
| `required_broken_lie_ids` | `List[str]` | ❌ | IDs de lies que devem ser quebradas para veredito `correct`. Default `[]`. |
| `suspects` | lista | ✅ | Lista de suspeitos. Deve ter ao menos o culpado. |
| `evidences` | lista | ✅ | Lista de evidências disponíveis. |
| `secrets` | lista | ✅ | Lista de segredos (relação evidência–suspeito). |
| `topics` | lista | ❌ | Temas rastreados pelo motor (detecção de intent). |
| `motives` | lista | ❌ | Motivações possíveis apresentadas ao jogador na acusação. |

---

### `SuspectConfig`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | string | ✅ | Slug estável único dentro do cenário (`"marina"`, `"joao_lima"`). |
| `name` | string | ✅ | Nome de exibição. |
| `backstory` | string | ❌ | Histórico pessoal do personagem. |
| `personality` | string | ❌ | Personalidade para o LLM (`"nervoso"`, `"arrogante"`, `"neutro"`). |
| `internal_note` | string | ❌ | Nota do autor, não exposta ao jogador. |
| `initial_statement` | string | ❌ | Declaração inicial mostrada ao entrar no interrogatório. |
| `final_phrase` | string | ❌ | Frase dita quando o suspeito está `is_closed`. |
| `true_timeline` | `List[str]` | ❌ | Linha do tempo verdadeira do suspeito (conhecimento interno do NPC). |
| `profile` | `TopicAffinityProfile` | ❌ | Perfil comportamental e dinâmico de fala (`pressure_tolerance`, `empathy_receptivity`, `speech`, etc.). |
| `flavor_slots` | lista de `FlavorSlotConfig` | ❌ | Slots narrativos cosméticos autorais acionados por palavras-chave. |
| `lies` | lista de `LieConfig` | ❌ | Mentiras que o suspeito sustenta e que podem ser quebradas. |
| `claims` | lista de `ClaimConfig` | ❌ | Asserções estruturadas feitas pelo suspeito que podem ser desafiadas. |
| `knowledge` | lista de `KnowledgeItemConfig` | ❌ | Conhecimentos do cenário que o suspeito pode revelar por tópico. |

---

### `TopicAffinityProfile` & `SpeechProfile`

Configurações psicológicas e dinâmicas de ritmo de fala do suspeito:

| Campo | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `pressure_tolerance` | float | `0.5` | Tolerância a pressão (0.0 frágil, 1.0 resistente). |
| `empathy_receptivity` | float | `0.5` | Receptividade a abordagens empáticas/calmas. |
| `repetition_irritability` | float | `0.5` | Irritabilidade ao enfrentar perguntas repetitivas. |
| `contradiction_fragility` | float | `0.5` | Rapidez com que quebra ao ser confrontado com contradições. |
| `speech` | `SpeechProfile` | `{}` | Perfil dinâmico de verbosidade e ritmo. |

#### `SpeechProfile`
| Campo | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `base_verbosity` | float | `0.5` | Extensão habitual da fala (0.0 conciso/lacônico, 1.0 muito falante). |
| `stress_verbosity_delta` | float | `0.0` | Modulação sob pressão (-1.0 fecha a boca/lacônico, +1.0 fala excessiva/ansiosa). |

---

### `EvidenceConfig`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | string | ✅ | Slug estável único dentro do cenário (`"faca_ensanguentada"`). |
| `name` | string | ✅ | Nome de exibição (ex: `"Faca Ensanguentada"`). |
| `description` | string | ❌ | Descrição pública da evidência. |
| `internal_note` | string | ❌ | Nota do autor. |
| `related_topic_id` | string | ❌ | `id` de um `TopicConfig`. Define contexto de relevância da evidência. |
| `is_mandatory` | bool | ❌ | Se `true`, a evidência é obrigatória para veredito `correct`. Default `false`. |

---

### `LieConfig`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | string | ✅ | Identificador único da mentira dentro do suspeito. |
| `statement` | string | ✅ | O texto da mentira que o NPC sustenta. |
| `topic_id` | string | ✅ | `id` de um `TopicConfig`. A mentira só pode ser quebrada nesse contexto. |
| `broken_by_evidence` | string | ✅ | `id` de uma `EvidenceConfig` que quebra esta mentira. |

> [!IMPORTANT]
> O `broken_by_evidence` deve ser o **slug estável** (`id`) da evidência no JSON, não o nome de exibição. O loader resolve automaticamente para o nome.

---

### `ClaimConfig`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `claim_id` | string | ✅ | Identificador único da claim dentro do suspeito. |
| `topic_id` | string | ✅ | `id` de um `TopicConfig`. A claim pertence a esse tópico. |
| `text` | string | ✅ | O texto da declaração da claim. |
| `claim_type` | string | ✅ | `"alibi"`, `"relationship"`, `"timeline"`, `"denial"`, `"motive"`, `"object"`, `"location"`. |
| `importance` | string | ❌ | `"low"`, `"medium"`, `"high"`, `"critical"`. Default `"medium"`. |
| `breakable_by_evidence_ids` | `List[str]` | ❌ | IDs de evidências que podem quebrar esta claim. Default `[]`. |
| `breakable_by_claim_ids` | `List[str]` | ❌ | IDs de outras claims que contradizem esta. Default `[]`. |
| `reveal_on_break` | `List[str]` | ❌ | IDs de secrets ou knowledges liberados quando quebrada. Default `[]`. |

---

### `KnowledgeItemConfig`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | string | ✅ | Identificador único do item dentro do suspeito. |
| `topic_id` | string | ✅ | `id` de um `TopicConfig`. O knowledge só é revelado quando esse tópico é tocado. |
| `kind` | string | ❌ | `"observed"`, `"heard"`, `"inferred"`, `"rumor"`, `"lie"`. Default `"observed"`. |
| `reliability` | string | ❌ | `"high"`, `"medium"`, `"low"`. Afeta quando as camadas são liberadas. |
| `content_layers` | `List[str]` | ✅ | Fatos revelados gradualmente. Camada 0 = básico, camadas seguintes = mais profundas. |

---

### `TopicConfig`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | string | ✅ | Slug único do tópico (`"alibi"`, `"faca"`, `"relacao_vitima"`). |
| `label` | string | ✅ | Rótulo legível para a interface. |
| `aliases` | `List[str]` | ❌ | Palavras-chave e sinônimos que ativam este tópico no motor de análise. |
| `is_sensitive` | bool | ❌ | Se `true`, penalidades de `out_of_context` são atenuadas. Default `false`. |
| `priority` | int | ❌ | Peso para resolução de conflitos quando múltiplos tópicos são detectados. Default `0`. |

---

### `MotivationConfig`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `key` | string | ✅ | Chave estável (`"financial_gain"`, `"revenge"`). |
| `label` | string | ✅ | Texto exibido ao jogador. |
| `description` | string | ❌ | Descrição interna, não exposta. |

---

### `SecretConfig`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `suspect` | string | ✅ | `id` do suspeito ao qual este segredo pertence. |
| `evidence` | string | ✅ | `id` da evidência que **revela** este segredo. |
| `content` | string | ✅ | O texto do segredo revelado. |
| `is_core` | bool | ❌ | Se `true`, este segredo conta para o progresso de interrogatório. Default `false`. |

---

## Regras de Referência

```
suspects[].id        → deve ser único no cenário
evidences[].id       → deve ser único no cenário
culprit              → deve existir em suspects[].id
true_motive_key      → deve existir em motives[].key
lies[].topic_id      → deve existir em topics[].id
lies[].broken_by_evidence → deve existir em evidences[].id
claims[].topic_id    → deve existir em topics[].id
claims[].breakable_by_evidence_ids[] → deve existir em evidences[].id
claims[].breakable_by_claim_ids[] → deve existir em outros suspects[].claims[].claim_id
knowledge[].topic_id → deve existir em topics[].id
evidences[].related_topic_id → deve existir em topics[].id (se definido)
secrets[].suspect    → deve existir em suspects[].id
secrets[].evidence   → deve existir em evidences[].id
required_broken_lie_ids[] → deve existir em algum suspects[].lies[].id
```

---

## Exemplo Mínimo Funcional

```json
{
  "scenario_code": "caso-minimo",
  "title": "O Caso Mínimo",
  "description": "Um cenário simples com 1 suspeito e 1 evidência.",
  "culprit": "joao",
  "motives": [
    { "key": "ganancia", "label": "Ganância" }
  ],
  "true_motive_key": "ganancia",
  "topics": [
    { "id": "alibi", "label": "Álibi", "aliases": ["onde estava", "noite do crime", "alibi"] }
  ],
  "suspects": [
    {
      "id": "joao",
      "name": "João Silva",
      "personality": "nervoso",
      "backstory": "Contador da empresa há 10 anos.",
      "initial_statement": "Eu não fiz nada de errado.",
      "lies": [
        {
          "id": "lie_alibi",
          "statement": "Estava em casa dormindo na noite do crime.",
          "topic_id": "alibi",
          "broken_by_evidence": "registro_hotel"
        }
      ]
    }
  ],
  "evidences": [
    {
      "id": "registro_hotel",
      "name": "Registro de Hotel",
      "description": "Check-in de João em hotel na cidade na noite do crime.",
      "related_topic_id": "alibi",
      "is_mandatory": true
    }
  ],
  "secrets": [
    {
      "suspect": "joao",
      "evidence": "registro_hotel",
      "content": "João estava em outra cidade, mas registrou presença no hotel para encobrir o paradeiro real.",
      "is_core": true
    }
  ],
  "required_broken_lie_ids": ["lie_alibi"]
}
```

> Execute `python validate_scenario.py scenarios/meu_cenario.json` para validar antes de rodar o servidor.

---

## Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `topic_id not found in topics` | Lie ou knowledge referencia topic inexistente | Verificar `topics[].id` |
| `broken_by_evidence not found` | Lie aponta para slug de evidência errado | Verificar `evidences[].id` |
| `Duplicate suspect id` | Dois suspects com mesmo `id` | Tornar todos os `id` únicos |
| `culprit not found in suspects` | Valor de `culprit` não existe em `suspects[].id` | Corrigir o campo `culprit` |
| `true_motive_key not in motives` | Chave de motivo verdadeiro não cadastrada | Adicionar motive ou corrigir a chave |
