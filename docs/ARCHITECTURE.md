# 🏛️ Arquitetura do Sistema — Detective AI

Este documento detalha o desenho arquitetural, os princípios de design, o modelo de dados e o ciclo de vida operacional do **Detective AI**.

---

## 1. Princípios Arquiteturais Centrais

O projeto é guiado por quatro princípios de engenharia:

1. **A IA é apenas a "Voz", nunca o "Cérebro" Decisório:**
   - Modelos de Linguagem (LLMs) são probabilísticos e propensos a alucinações. O backend determinístico em Python toma **100% das decisões lógicas** do jogo (se uma mentira quebrou, se um segredo foi revelado, como a pressão subiu, se o suspeito se fechou). O LLM é instruído exclusivamente para interpretar teatralmente o resultado dramático já decidido pelo sistema.
2. **Garantia de Vazamento Zero de Segredos (Zero-Spoiler Isolation):**
   - Um NPC nunca recebe no prompt informações que ele não tem permissão para admitir. Mesmo que o suspeito conheça o assassino em sua biografia de fundo, seu contexto de renderização só contém fatos já formalmente destravados pelo jogador.
3. **Persistência Atômica de Turno (ACID):**
   - Cada turno de interrogatório é uma transação atômica no SQLite. Se a chamada ao LLM falhar ou houver exceção, o rollback do banco garante que nenhum estado inconsistente de pressão ou paciência permaneça corrompido.
4. **Acoplamento Fraco e Testabilidade Isolada:**
   - Todos os serviços de domínio (`claim_resolution`, `move_classification`, `verdict_service`, `topic_state`) são funções e classes desacopladas de I/O de rede, permitindo execução de testes unitários ultrarrápidos em memória.

---

## 2. Visão em Camadas (Layered Architecture)

```
[ Frontend: SPA (Vanilla JS / HTML / CSS) ]
                   │
                   ▼ (HTTP REST / JSON)
┌─────────────────────────────────────────────────────────┐
│ 1. API Layer (app/api/)                                 │
│    - Roteadores FastAPI: sessions.py, scenarios.py      │
│    - Contratos de Entrada/Saída: Pydantic v2 Schemas    │
│    - Handlers de Exceção Global (app/core/)             │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Orchestration Layer (app/services/)                  │
│    - interrogation_turn_service.py                      │
│    - session_service.py / session_finalize_service.py   │
└──────────────────────────┬──────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐
│ 3. Domain & Mechanics         │ │ 4. AI & Prompt Pipeline       │
│    - move_classification      │ │    - prompt_builder           │
│    - topic_state_service      │ │    - render_context_builder   │
│    - claim_resolution_service │ │    - ai_adapter_openai        │
│    - reveal_policy_service    │ │    - ai_adapter_dummy         │
│    - verdict_service          │ │    - npc_response_guard       │
│    - narrative_memory         │ └───────────────────────────────┘
└───────────────┬───────────────┘                 │
                │                                 │
                └─────────────────┬───────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Infrastructure Layer (app/infra/)                    │
│    - db.py (Engine SQLAlchemy, SessionLocal)            │
│    - db_models.py (Tabelas SQLite)                      │
│    - scenario_loader.py (Loader de Cenários JSON)       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Modelo de Dados (Database Schema)

O banco de dados SQLite (`game.db`) é estruturado em modelos relacionais via SQLAlchemy:

### Tabelas Estáticas / Pré-carregadas:
- **`scenarios` (`ScenarioModel`):**
  - Identificador único, título, descrição, `culprit` (slug do culpado), `required_broken_lie_ids` e `true_motive_key`.
- **`suspects` (`SuspectModel`):**
  - Vinculado ao cenário. Armazena `name`, `backstory`, `personality`, `initial_statement`, `final_phrase`, `true_timeline` e `lies`.
- **`evidences` (`EvidenceModel`):**
  - Pistas físicas/documentais disponíveis para a investigação (`name`, `description`).
- **`secrets` (`SecretModel`):**
  - Fatos ocultos do cenário associados a um suspeito e/ou evidência, com nível de profundidade (`layer`: 1, 2, 3).
- **`topics` (`TopicModel`):**
  - Tópicos de discussão configurados com palavras-chave, flag de sensibilidade (`is_sensitive`) e limites de calor.

### Tabelas Dinâmicas de Sessão:
- **`sessions` (`SessionModel`):**
  - Sessão do jogador, cenário associado, data de criação e status (`in_progress` | `finished`).
- **`session_suspects` (`SessionSuspectModel`):**
  - Estado psicológico individual de cada suspeito na sessão:
    - `patience` (Float): Paciência restante (0.0 a 100.0).
    - `pressure` (Float): Pressão psicológica acumulada (0.0 a 100.0).
    - `rapport` (Float): Nível de empatia/sintonia com o detetive.
    - `stance` (Enum): Postura atual (`neutral`, `defensive`, `pressured`, `cooperative`).
    - `is_closed` (Boolean): Indica se o suspeito se calou em definitivo.
    - `last_topic_id` (String): Último tópico abordado.
    - `revealed_secrets` (JSON): Lista de IDs de segredos já admitidos pelo suspeito.
- **`session_claim_states` (`SessionClaimStateModel`):**
  - Rastreamento fino de cada alegação/mentira do suspeito na sessão (`is_broken`, turno de quebra).
- **`messages` (`MessageModel`):**
  - Histórico de turnos gravados na sessão (`sender_type`: "player" ou "npc", texto, evidência vinculada, timestamp).

---

## 4. Máquina de Estados Psicológica do Suspeito (FSM)

Cada suspeito opera sob um autômato psicológico alimentado pelos inputs do jogador:

```
                  ┌──────────────────────┐
                  │       NEUTRAL        │
                  │  (Padrão no início)  │
                  └──────────┬───────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
(Pressure > 80)     (Patience < 10)    (Rapport > 50 &
            │                │          Pressure < 30)
            ▼                ▼                ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │  PRESSURED  │  │  DEFENSIVE  │  │ COOPERATIVE │
     │  (Vulnerável│  │ (Recusa/    │  │ (Revela mais│
     │   a falhas) │  │  desvios)   │  │  detalhes)  │
     └──────┬──────┘  └──────┬──────┘  └─────────────┘
            │                │
            └────────┬───────┘
                     │ (Patience == 0)
                     ▼
              ┌─────────────┐
              │  IS_CLOSED  │
              │ (Suspeito   │
              │  não fala)  │
              └─────────────┘
```

### Variáveis e Efeitos:
- **Paciência (`patience`):** Diminui com perguntas repetitivas, insistência no mesmo tópico esgotado ou acusações infundadas. Quando atinge zero, o suspeito fecha o diálogo (`is_closed = True`).
- **Pressão (`pressure`):** Sobe ao ser confrontado com evidências irrefutáveis, tópicos sensíveis ou contradições. Altas taxas de pressão induzem lapsos, deflexões ansiosas ou quebra de mentiras.
- **Empatia (`rapport`):** Construído com exploração calma e contextual. Suspeitos cooperativos colaboram fornecendo pistas secundárias sobre outros investigados.

---

## 5. Ciclo de Vida do Turno de Interrogatório

Quando o jogador envia uma pergunta (`POST /sessions/{id}/suspects/{id}/messages`), o `run_interrogation_turn` executa o pipeline em 8 etapas:

```
[Input do Jogador (Texto + Evidência)]
                 │
                 ▼
1. Análise Semântica (Move Classifier)
   -> Identifica Intent (ask, press, confront, etc.)
   -> Identifica MoveType (explore, deepen, reframe, pressure, confront)
   -> Detecta Tópico Ativo e Sensibilidade
                 │
                 ▼
2. Contexto Conversacional & Memória Narrativa
   -> Lê janela recente de mensagens
   -> Constrói ConversationMemory e histórico
                 │
                 ▼
3. Resolução de Claims & Mentiras
   -> Confronta se a evidência apresentada contradiz alguma alegação ativa
   -> Se verdadeiro: quebra a mentira e registra no Case File
                 │
                 ▼
4. Atualização de Estado Psicológico
   -> Aplica deltas em patience, pressure e rapport
   -> Atualiza stance (neutral, defensive, pressured, cooperative)
                 │
                 ▼
5. Política de Revelação de Segredos
   -> Avalia se níveis de pressão ou empatia destravaram novos segredos
                 │
                 ▼
6. Construção do Render Context
   -> Define response_mode (guarded, pressured_deflection, contradiction_repair, etc.)
   -> Consolida fatos estritamente permitidos para fala neste turno
                 │
                 ▼
7. Síntese do Prompt & Chamada LLM
   -> Monta prompt rigoroso anti-spoiler
   -> Invoca OpenAI API (ou adapter Dummy)
   -> Passa pelo Response Guard para checagem de consistência
                 │
                 ▼
8. Persistência & Retorno
   -> Salva mensagens e novo estado no SQLite
   -> Retorna resposta ao frontend
```

---

## 6. Sistema de Julgamento & Veredito

Ao decidir acusar (`POST /sessions/{session_id}/accuse`), o jogador submete:
- **`suspect_id`**: Quem ele acredita ser o culpado.
- **`evidence_ids`**: Provas que sustentam a acusação.
- **`motive_key`**: A motivação do crime.

O `verdict_service.py` avalia:
1. **Culpado correto?** Compara com o campo `culprit` do cenário.
2. **Mentiras essenciais quebradas?** Verifica se todas as `required_broken_lie_ids` foram desmascaradas durante o interrogatório.
3. **Motivação descoberta?** Compara com o `true_motive_key` do caso.
4. **Evidências suficientes?** Valida se as evidências submetidas têm vínculo comprovado com o culpado.

**Resultados Possíveis:**
- `correct`: Acusação perfeita, caso solucionado com mérito policial.
- `partial`: O suspeito era o culpado, mas faltaram provas suficientes ou a motivação correta.
- `wrong`: Acusação equivocada; um inocente foi preso ou as evidências são completamente insuficientes.
