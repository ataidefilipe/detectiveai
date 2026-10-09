# Guia de Verificação e Auditoria de Traces (Railway / Produção)

Este documento descreve o processo técnico utilizado para inspecionar, auditar e avaliar conversas, mecânicas de jogo e telemetria de sessões em execução no ambiente do Railway.

---

## 1. Visão Geral da Arquitetura de Telemetria

O sistema possui três camadas complementares de observabilidade:

1. **Railway Logs & Streams**: Logs de deploy/runtime e logs de proxy HTTP capturados na infraestrutura.
2. **Logger de Telemetria (`detective-telemetry`)**: Emite linhas JSON estruturadas a cada turno de interrogatório (`interrogation_turn`) para stdout.
3. **Turn Logs Analíticos Persistidos (`TurnLogModel`)**: Armazenados no banco de dados relacional (PostgreSQL), salvando o snapshot completo de cada turno (análise da mensagem, transições de estado, efeitos mecânicos, prompt do LLM e resposta da IA).

---

## 2. Passo a Passo do Processo de Investigação

### Passo 1: Localização do Projeto e Serviços no Railway
O primeiro passo é mapear a infraestrutura ativa utilizando as ferramentas do MCP do Railway:

1. **Listar projetos**: Identificar o projeto alvo (`detective-ai`).
   * *Tool*: `list-projects`
   * *Resultado*: Project ID `47f14c43-5f1a-403d-9070-5fa6dd8b0083`.
2. **Listar serviços e ambientes**: Obter os IDs de ambiente e de serviço da aplicação e do banco.
   * *Tool*: `list-services`
   * *Resultado*: Environment `production`, Service `detective-ai` (`b866edb3-2dd4-46b0-b4ed-4ab384ae1de6`) e Service `Postgres`.
3. **Verificar domínios públicos**: Descobrir a URL de acesso à API em produção.
   * *Tool*: `list-domains`
   * *Resultado*: `https://detective-ai-production.up.railway.app`.

### Passo 2: Inspeção dos Logs Brutos e Telemetria em Produção
Para verificar a atividade recente e identificar quais sessões e turnos ocorreram:

1. **Buscar logs de deploy e HTTP**:
   * *Tool*: `get-logs` com tipos `deploy` e `http`.
   * *Resultado*: Localização da criação da **Sessão 3** (`POST /sessions`), requisições sucessivas para `POST /sessions/3/suspects/1/messages` e eventos estruturados emitidos pelo logger `detective-telemetry`:
     ```json
     {"event": "interrogation_turn", "session_id": 3, "suspect_id": 1, "msg_analysis": {...}, "state_transition": {...}}
     ```

### Passo 3: Extração dos Dados Analíticos da Sessão
Com o domínio identificado e a sessão localizada, consultam-se os endpoints de auditoria e leitura da API:

1. **Metadados Gerais e Case File**:
   * `GET /sessions/3` (Resumo da sessão e cenário).
   * `GET /sessions/3/suspects` (Lista de suspeitos e declarações iniciais).
   * `GET /sessions/3/evidences` (Lista de evidências disponíveis no cenário).
   * `GET /debug/sessions/3/suspects/1/status` (Estado interno: paciência, pressão, stance, tópicos e claims).
   * `GET /sessions/3/case-file` (Fatos confirmados, trilhas e evidências efetivas/ineficazes).
2. **Histórico Cronológico do Chat**:
   * `GET /sessions/3/suspects/1/messages` (Lista completa das mensagens trocadas).
3. **Traces Completos dos Turnos (Logs com Prompts)**:
   * `GET /sessions/3/logs/turns?suspect_id=1&include_prompt=true`
   * Este endpoint extrai o histórico registrado em `TurnLogModel`, contendo para cada turno:
     * Texto e evidência enviada pelo jogador.
     * Resultado da classificação de mensagem (intent, move_type, tópicos, sensibilidade).
     * Transição de estado calculada (`state_before` vs `state_after`).
     * Efeitos mecânicos e narrativos (segredos revelados, claims quebradas).
     * Metadados da IA (modelo, latência, modo de resposta, prompt do sistema e histórico completo montado).

### Passo 4: Triagem e Diagnóstico Turno a Turno
Com o JSON analítico em mãos, executa-se a avaliação cruzada das mecânicas:

1. **Validação Heurística vs Semântica**:
   * Checagem do campo `analysis_provider` nos logs.
   * Constatou-se se os turnos usaram `heuristic` ou `openai` e se houve falhas de reconhecimento por sensibilidade a acentos (ex.: *"onde voce estava"* vs alias *"onde você estava"*).
2. **Validação de Evidências e Contexto**:
   * Avaliação do `evidence_effect`:
     * `revealed_secret` e `broke_claim`: Evidência correta apresentada no momento oportuno (Turno 12).
     * `none`: Evidência sem relação com a suspeita (Turno 17 - caneca de café).
     * `out_of_context`: Evidência apresentada sem contexto prévio ou vínculo de tópico (Turno 18 - cartão de acesso com mensagem *"OLHA SO"*).
3. **Auditoria de Prompts e Respostas da IA**:
   * Inspeção do `render_context`: checagem das seções `must_say`, `must_not_say`, limites de frases/palavras e conformidade do tom (`npc_stance`).
   * Análise de latência do provedor e tempo de resposta.

---

## 3. Comandos e Ferramentas Práticas

### 3.1. Coleta Rápida via Terminal (PowerShell)

```powershell
$baseUrl = "https://detective-ai-production.up.railway.app"
$sessionId = 3
$suspectId = 1

# 1. Baixar traces analíticos com prompts
Invoke-RestMethod -Uri "$baseUrl/sessions/$sessionId/logs/turns?suspect_id=$suspectId&include_prompt=true" | `
  ConvertTo-Json -Depth 10 | Set-Content -Path "session_${sessionId}_turns.json" -Encoding utf8

# 2. Baixar status atual do suspeito e case-file
Invoke-RestMethod -Uri "$baseUrl/debug/sessions/$sessionId/suspects/$suspectId/status" | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "$baseUrl/sessions/$sessionId/case-file" | ConvertTo-Json -Depth 5
```

### 3.2. Script Python para Resumo dos Turnos

```python
import json

with open("session_3_turns.json", "r", encoding="utf-8-sig") as f:
    data = json.load(f)

for t in data.get("turns", []):
    num = t.get("turn_number")
    player = t.get("player_text")
    npc = t.get("npc_text")
    ev = t.get("evidence_id")
    prov = t.get("analysis_provider")
    topic = t.get("primary_topic_id")
    eff = t.get("evidence_effect")
    sb = t.get("state_before", {})
    sa = t.get("state_after", {})
    
    print(f"Turno {num} | Ev: {ev} | Prov: {prov} | Tópico: {topic} | Efeito: {eff}")
    print(f"  Jogador: {player}")
    print(f"  Marina:  {npc}")
    print(f"  Estado:  Paciência: {sb.get('patience')} -> {sa.get('patience')} | Pressão: {sb.get('pressure')} -> {sa.get('pressure')}")
    print("-" * 60)
```

---

## 4. Checklist para Auditorias Futuras

- [ ] **Variáveis de Ambiente**: Confirmar se `MESSAGE_CLASSIFIER_PROVIDER` está configurado (`heuristic` vs `openai`).
- [ ] **Logs de Aplicação**: Filtrar logs do Railway por `detective-telemetry` para verificar ocorrência de turnos e exceções.
- [ ] **Identificação de Falsos Negativos**: Verificar se perguntas naturais do jogador falharam na detecção de tópicos existentes no cenário.
- [ ] **Penalidades Indesejadas**: Monitorar quedas súbitas de paciência decorrentes de `out_of_context` e validar se a evidência realmente carecia de contexto.
- [ ] **Densidade de Informação**: Inspecionar se o campo `must_say` não está sobrecarregando o LLM com muitas revelações em um único turno.

---

## 5. Histórico de Melhorias Decorrentes da Auditoria (Sessão 3)

Com base na auditoria da Sessão 3 de Marina Souza, 5 melhorias foram implementadas e validadas:

1. **Injeção de Claims Ativas no Prompt (`active_claims`)**:
   - As claims não quebradas agora são explicitadas como a versão oficial/álibi defensável do suspeito (`== SUA VERSAO OFICIAL DOS FATOS ==`). O suspeito tem base narrativa para sustentar sua versão antes de ser confrontado com provas.
2. **Injeção de Evidência Apresentada (`presented_evidence`)**:
   - Nome e descrição pública da evidência concreta apresentada pelo detetive são passados no prompt em `=== EVIDENCIA APRESENTADA PELO DETETIVE NESTE TURNO ===`. Evita que o NPC pergunte "o que é isso?" para um objeto que está na mesa.
3. **Ordem de Avaliação da Política de Revelação (Baseline pré-turno)**:
   - A avaliação de camada em `reveal_policy_service.py` avalia com a paciência baseline pré-turno (`eval_state`), impedindo que a penalidade de sensibilidade do turno corrente bloqueie a Camada 1 do próprio tópico recém-tocado.
4. **Camada Pública de Trabalho/Rotina no Cenário (`rotina_trabalho`)**:
   - Adicionado tópico não sensível de rotina corporativa e conhecimentos correspondentes para todos os 4 suspeitos em `scenarios/piloto.json`, permitindo perguntas cotidianas de interrogatório sem perda de paciência ou bloqueio de fala.
5. **Teto de `must_say` por Turno (`MAX_MUST_SAY_PER_TURN = 2`)**:
   - Limitação para até 2 fatos obrigatórios em `must_say`. Excedentes fluem para `may_say` (opcionais), prevenindo monólogos expositivos que descarregavam múltiplos conhecimentos em um único parágrafo.

