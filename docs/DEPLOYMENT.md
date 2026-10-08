# 🚀 Guia de Deploy em Produção — Railway

Este documento descreve como o **Detective AI** é empacotado, configurado e publicado em produção utilizando a plataforma **Railway**.

---

## 🌐 Informações do Ambiente Ativo

- **URL Pública:** [https://detective-ai-production.up.railway.app](https://detective-ai-production.up.railway.app)
- **Projeto Railway:** `detective-ai` (`47f14c43-5f1a-403d-9070-5fa6dd8b0083`)
- **Serviço Railway:** `detective-ai` (`b866edb3-2dd4-46b0-b4ed-4ab384ae1de6`)
- **Ambiente:** `production` (`1ccf1048-c156-4c28-8a4a-ad353632e652`)
- **Repositório Conectado:** `ataidefilipe/detectiveai` (branch `main`)

---

## 🏗️ Estratégia de Empacotamento (Full-Stack Unificado)

Para manter a simplicidade operacional e evitar custos com múltiplos serviços ou microserviços desnecessários:

1. **Serviço Único:** O backend FastAPI serve tanto os endpoints REST (`/sessions`, `/scenarios`) quanto a interface web do usuário (`frontend/index.html`) através da rota raiz (`/`) e `/static`.
2. **Nixpacks Automático:** O Railway utiliza o builder **Nixpacks** para detectar automaticamente a versão do Python através de `requirements.txt`.
3. **Ponto de Partida (`Procfile` & `railway.json`):**
   - O comando de execução é definido no [Procfile](file:///d:/Python%20Projetos/detective_ai/Procfile):
     ```procfile
     web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
     ```
   - O [railway.json](file:///d:/Python%20Projetos/detective_ai/railway.json) define políticas de reinicialização em caso de falha transitória:
     ```json
     {
       "$schema": "https://railway.app/railway.schema.json",
       "build": {
         "builder": "NIXPACKS"
       },
       "deploy": {
         "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}",
         "restartPolicyType": "ON_FAILURE",
         "restartPolicyMaxRetries": 10
       }
     }
     ```

---

## 🔑 Variáveis de Ambiente no Railway

No painel do Railway (ou via ferramenta MCP `set-variables`), as seguintes variáveis devem estar configuradas no serviço:

| Variável | Valor Recomendado | Finalidade |
|----------|-------------------|------------|
| `OPENAI_API_KEY` | `sk-proj-...` | Credencial para chamar o modelo da OpenAI |
| `NPC_AI_PROVIDER` | `openai` | Habilita o adaptador real de IA (ou `dummy` para testes) |
| `OPENAI_MODEL` | `gpt-5-mini` | Modelo utilizado nas conversas com os suspeitos |
| `PORT` | *(injetada pelo Railway)* | Porta em que o container escuta requisições |

---

## 🔄 Fluxo de Deploy Contínuo (CI/CD)

O serviço está configurado com integração contínua vinculada ao GitHub:

1. Desenvolva as alterações localmente.
2. Valide com a suíte de testes: `pytest`.
3. Faça commit e push para a branch `main`:
   ```bash
   git add .
   git commit -m "feat: sua alteração"
   git push origin main
   ```
4. O Railway detecta o novo commit via Webhook do GitHub, inicia um novo build Nixpacks e realiza um **Rolling Deploy** sem indisponibilidade.

---

## 💾 Persistência de Dados (SQLite e Volumes)

- **Comportamento Padrão:** O banco SQLite `game.db` é inicializado no contêiner. No startup do FastAPI, a função `bootstrap_game()` garante que todas as tabelas sejam criadas e que os cenários contidos na pasta `scenarios/*.json` sejam carregados automaticamente de forma idempotente.
- **Volumes Persistentes no Railway (Opcional):**
  - Caso seja necessário reter o estado de sessões antigas entre reinicializações e novos deploys, um Railway Volume pode ser criado e montado no caminho do banco (ex: `/data/game.db`).
  - Para criar um volume via Railway MCP:
    ```json
    { "serviceId": "...", "mountPath": "/data" }
    ```
  - E apontar `SQLALCHEMY_DATABASE_URL = "sqlite:////data/game.db"` em `app/infra/db.py`.

---

## 🛠️ Diagnóstico e Observabilidade

Para inspecionar a saúde do serviço em produção:

- **Logs de Execução (Deploy Logs):**
  - Via Railway MCP: `get-logs` com tipos `["deploy"]` ou `["build"]`.
  - Via Dashboard do Railway na aba **Logs**.
- **Métricas:**
  - `http-requests`, `http-error-rate` e `http-response-time` via ferramentas MCP do Railway.
