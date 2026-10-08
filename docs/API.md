# 🔌 Especificação da API REST — Detective AI

Esta documentação descreve todos os endpoints disponibilizados pela API do **Detective AI**, incluindo contratos de entrada, saída, códigos de status HTTP e exemplos práticos.

---

## 📌 Informações Gerais

- **Base URL (Local):** `http://localhost:8000`
- **Base URL (Produção):** `https://detective-ai-production.up.railway.app`
- **Formato:** JSON (`application/json`)
- **Documentação Interativa (Swagger/OpenAPI):** `/docs`
- **Redoc:** `/redoc`

---

## 📑 Índice de Endpoints

1. [Infraestrutura e Frontend](#1-infraestrutura-e-frontend)
   - `GET /health` — Verificação de saúde da aplicação
   - `GET /` — Interface gráfica web (Frontend SPA)
2. [Cenários (Scenarios)](#2-cenários-scenarios)
   - `GET /scenarios` — Listar cenários disponíveis
   - `GET /scenarios/{scenario_id}` — Detalhes de um cenário
3. [Sessões de Jogo (Sessions)](#3-sessões-de-jogo-sessions)
   - `POST /sessions` — Iniciar uma nova sessão de investigação
   - `GET /sessions/{session_id}` — Visão geral da sessão ativa
4. [Interrogatório (Chat & Messages)](#4-interrogatório-chat--messages)
   - `POST /sessions/{session_id}/suspects/{suspect_id}/messages` — Executar turno de interrogatório
   - `GET /sessions/{session_id}/suspects/{suspect_id}/messages` — Obter histórico de mensagens com o suspeito
5. [Dossiê da Investigação (Case File)](#5-dossiê-da-investigação-case-file)
   - `GET /sessions/{session_id}/case-file` — Obter dossiê consolidado
6. [Acusação & Veredito Final (Verdict)](#6-acusação--veredito-final-verdict)
   - `POST /sessions/{session_id}/accuse` — Realizar acusação formal e concluir caso
7. [Logs Analíticos (Analytics & Logs)](#7-logs-analíticos-analytics--logs)
   - `GET /sessions/{session_id}/logs/turns` — Histórico analítico dos turnos
   - `GET /sessions/{session_id}/logs/verdict` — Log analítico do veredito final

---

## 1. Infraestrutura e Frontend

### `GET /health`
Verifica se o servidor e a aplicação estão operacionais.

**Resposta `200 OK`:**
```json
{
  "status": "ok"
}
```

---

### `GET /`
Retorna a página única da interface web do jogo (`text/html`).

---

## 2. Cenários (Scenarios)

### `GET /scenarios`
Lista todos os casos criminais disponíveis no banco de dados.

**Resposta `200 OK`:**
```json
[
  {
    "id": 1,
    "title": "O Caso do Escritório Trancado",
    "description": "Um funcionário importante da empresa Solarium Corp foi encontrado morto dentro de uma sala trancada por dentro."
  }
]
```

---

### `GET /scenarios/{scenario_id}`
Retorna os detalhes de um cenário específico.

**Parâmetros de Rota:**
- `scenario_id` (int): Identificador do cenário.

**Resposta `200 OK`:**
```json
{
  "id": 1,
  "title": "O Caso do Escritório Trancado",
  "description": "Um funcionário importante da empresa Solarium Corp...",
  "suspects": [
    {
      "id": 1,
      "name": "Marina Souza",
      "backstory": "Assistente financeira da empresa..."
    }
  ],
  "evidences": [
    {
      "id": 1,
      "name": "Relatório Financeiro Adulterado",
      "description": "Planilha com discrepâncias contábeis no último trimestre."
    }
  ],
  "motive_options": [
    {
      "key": "financial_gain",
      "label": "Ganhos Financeiros e Desvio de Dinheiro"
    },
    {
      "key": "revenge",
      "label": "Vingança Pessoal"
    }
  ]
}
```

---

## 3. Sessões de Jogo (Sessions)

### `POST /sessions`
Inicializa uma nova sessão de investigação a partir de um cenário.

**Payload:**
```json
{
  "scenario_id": 1
}
```

**Resposta `200 OK`:**
```json
{
  "session_id": 1,
  "scenario_id": 1,
  "status": "in_progress"
}
```

---

### `GET /sessions/{session_id}`
Retorna a visão geral da sessão do jogador, incluindo suspeitos, status de investigações e evidências liberadas.

**Resposta `200 OK`:**
```json
{
  "session_id": 1,
  "status": "in_progress",
  "scenario": {
    "id": 1,
    "title": "O Caso do Escritório Trancado",
    "description": "...",
    "motive_options": [...]
  },
  "suspects": [
    {
      "suspect_id": 1,
      "name": "Marina Souza",
      "backstory": "...",
      "stance": "neutral",
      "is_closed": false
    }
  ],
  "evidences": [
    {
      "id": 1,
      "name": "Relatório Financeiro Adulterado",
      "description": "..."
    }
  ]
}
```

---

## 4. Interrogatório (Chat & Messages)

### `POST /sessions/{session_id}/suspects/{suspect_id}/messages`
Executa um turno atômico de interrogatório. Envia a fala do detetive e opcionalmente uma evidência apresentada para confrontar o suspeito.

**Payload:**
```json
{
  "text": "Você disse que nunca teve acesso a este documento, mas veja este relatório assinado por você.",
  "evidence_id": 1
}
```

**Resposta `200 OK`:**
```json
{
  "player_message": {
    "id": 1,
    "session_id": 1,
    "suspect_id": 1,
    "sender_type": "player",
    "text": "Você disse que nunca teve acesso...",
    "evidence_id": 1,
    "timestamp": "2026-10-08T15:20:00Z"
  },
  "npc_message": {
    "id": 2,
    "session_id": 1,
    "suspect_id": 1,
    "sender_type": "npc",
    "text": "Tudo bem! Eu assinei sim, mas fui coagida pelo diretor!",
    "evidence_id": null,
    "timestamp": "2026-10-08T15:20:03Z"
  },
  "suspect_state": {
    "progress": 35.0,
    "is_closed": false,
    "stance": "pressured",
    "patience": 42.0,
    "pressure": 68.5,
    "rapport": 15.0,
    "broken_claim_ids": ["marina_claim_no_report_access"],
    "last_topic_id": "financial_records",
    "response_mode": "contradiction_repair"
  },
  "turn_feedback": {
    "lie_broken": true,
    "feedback_message": "A contradição foi exposta! O suspeito foi forçado a recuar."
  }
}
```

---

### `GET /sessions/{session_id}/suspects/{suspect_id}/messages`
Retorna todo o histórico cronológico de mensagens trocadas com o suspeito.

**Resposta `200 OK`:**
```json
[
  {
    "id": 1,
    "sender_type": "player",
    "text": "Onde você estava às 22h?",
    "evidence_id": null,
    "timestamp": "2026-10-08T15:00:00Z"
  },
  {
    "id": 2,
    "sender_type": "npc",
    "text": "Eu estava no meu apartamento dormindo.",
    "evidence_id": null,
    "timestamp": "2026-10-08T15:00:02Z"
  }
]
```

---

## 5. Dossiê da Investigação (Case File)

### `GET /sessions/{session_id}/case_file`
Retorna as descobertas consolidadas da sessão, agrupadas para orientar a formulação da acusação.

**Resposta `200 OK`:**
```json
{
  "discovered_secrets": [
    {
      "id": 1,
      "suspect_id": 1,
      "secret_description": "Marina desviou 50 mil reais na semana passada.",
      "layer": 1
    }
  ],
  "broken_claims": [
    {
      "claim_id": "marina_claim_no_report_access",
      "suspect_id": 1,
      "original_statement": "Nunca tive contato com as contas da empresa.",
      "broken_by_evidence_name": "Relatório Financeiro Adulterado"
    }
  ],
  "motive_clues": [
    {
      "motive_key": "financial_gain",
      "clue_text": "A vítima ameaçou denunciar o desvio fiscal para a polícia."
    }
  ]
}
```

---

## 6. Acusação & Veredito Final (Verdict)

### `POST /sessions/{session_id}/accuse`
Finaliza a investigação formalizando a acusação contra um suspeito.

**Payload:**
```json
{
  "suspect_id": 1,
  "evidence_ids": [1, 3],
  "motive_key": "financial_gain"
}
```

**Resposta `200 OK` (Veredito Correto):**
```json
{
  "session_id": 1,
  "status": "finished",
  "verdict": {
    "verdict_type": "correct",
    "is_culprit_correct": true,
    "is_motive_correct": true,
    "required_lies_broken": true,
    "summary": "Excelente trabalho, detetive! Você identificou o culpado, comprovou o motivo e desmontou todas as mentiras apresentadas durante o interrogatório.",
    "score": 100
  }
}
```

**Resposta `200 OK` (Veredito Parcial ou Incorreto):**
```json
{
  "session_id": 1,
  "status": "finished",
  "verdict": {
    "verdict_type": "partial",
    "is_culprit_correct": true,
    "is_motive_correct": false,
    "required_lies_broken": true,
    "partial_reasons": [
      "O suspeito acusado era o assassino, mas a motivação indicada não condiz com as provas obtidas."
    ],
    "summary": "Você acertou o culpado, mas a acusação foi incompleta perante o tribunal.",
    "score": 60
  }
}
```

---

## 7. Logs Analíticos (Analytics & Logs)

### `GET /sessions/{session_id}/logs/turns`
Retorna a lista cronológica de turnos de interrogatório da sessão com todos os dados analíticos registrados (intenção, jogada, deltas de pressão/paciência, efeitos de evidências, modo de resposta e telemetria da IA).

**Parâmetros de Query:**
- `suspect_id` *(opcional, int)*: Filtra apenas os turnos realizados com um suspeito específico.
- `include_prompt` *(opcional, bool, padrão `false`)*: Se `true`, inclui o payload completo do prompt enviado à LLM naquele turno.

**Resposta `200 OK`:**
```json
{
  "session_id": 1,
  "total_turns": 1,
  "turns": [
    {
      "id": 1,
      "session_id": 1,
      "suspect_id": 1,
      "turn_number": 1,
      "created_at": "2026-10-08T14:49:48.042123",
      "player_message_id": 10,
      "npc_message_id": 11,
      "player_text": "Onde você estava na hora do crime?",
      "npc_text": "Eu estava no meu escritório trabalhando...",
      "evidence_id": null,
      "intent": "ask",
      "move_type": "explore",
      "primary_topic_id": "alibi",
      "analysis_provider": "heuristic",
      "evidence_effect": "none",
      "response_mode": "neutral_answer",
      "state_before": {
        "patience": 50.0,
        "pressure": 0.0,
        "rapport": 0.0,
        "stance": "neutral"
      },
      "state_after": {
        "patience": 50.0,
        "pressure": 2.0,
        "rapport": 0.0,
        "stance": "neutral"
      },
      "analysis": {
        "intent": "ask",
        "novelty": "new",
        "sensitivity_hit": "none",
        "confidence": 1.0
      },
      "transition": {
        "conversation_effect": "new_topic",
        "npc_shift": "none",
        "state_deltas": { "pressure": 2.0 }
      },
      "effects": {
        "revealed_secrets": [],
        "newly_broken_claims": [],
        "allowed_knowledge": []
      },
      "ai": {
        "adapter": "DummyNpcAIAdapter",
        "latency_ms": 12,
        "guard_blocked": false
      },
      "prompt": null
    }
  ]
}
```

---

### `GET /sessions/{session_id}/logs/verdict`
Retorna o log analítico consolidado do veredito final da sessão (registrado no momento da acusação).

**Resposta `200 OK`:**
```json
{
  "id": 1,
  "session_id": 1,
  "scenario_id": 1,
  "created_at": "2026-10-08T15:20:10.123456",
  "result_type": "correct",
  "chosen_suspect_id": 1,
  "real_culprit_id": 1,
  "chosen_motive_key": "financial_gain",
  "motive_result": "correct",
  "evidence_ids": [1, 2],
  "verdict": {
    "result_type": "correct",
    "missing_evidence_ids": [],
    "required_evidence_ids": [1, 2],
    "chosen_suspect_id": 1,
    "real_culprit_id": 1,
    "chosen_motive_key": "financial_gain",
    "motive_result": "correct",
    "reason_codes": [],
    "missing_claim_ids": []
  },
  "session_summary": {
    "duration_seconds": 320,
    "total_turns": 14,
    "turns_per_suspect": {
      "1": 8,
      "2": 6
    }
  }
}
```

---

## 🛑 Tratamento de Erros e Exceções

Erros de negócio e violações de regras utilizam `DomainError` e retornam respostas estruturadas com códigos HTTP adequados:

| Código HTTP | Significado | Exemplo |
|-------------|-------------|---------|
| `400 Bad Request` | Regra de negócio violada | Sessão já encerrada, suspeito recusou falar |
| `404 Not Found` | Recurso inexistente | Sessão, suspeito ou evidência não encontrados |
| `422 Unprocessable Entity` | Erro de validação Pydantic | Parâmetro obrigatório ausente ou formato incorreto |
| `500 Internal Server Error` | Falha inesperada no servidor | Erro de conexão com banco de dados |

**Formato padrão de erro:**
```json
{
  "detail": "Suspeito 999 não encontrado na sessão 1."
}
```
