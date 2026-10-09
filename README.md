# 🕵️ Detective AI — Jogo Investigativo com Interrogatório por IA

> Um jogo de dedução e investigação criminal onde você é o detetive. Interrogue suspeitos movidos por inteligência artificial, quebre álibis usando evidências, monte seu dossiê e formule a acusação final perante as autoridades.

[![Deploy on Railway](https://railway.com/button.svg)](https://detective-ai-production.up.railway.app)
[![Tests](https://img.shields.io/badge/tests-328%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-009688)]()

---

## 🌐 Jogue Online (Produção)

O jogo está publicado e rodando no Railway com banco de dados PostgreSQL persistente:
👉 **[https://detective-ai-production.up.railway.app](https://detective-ai-production.up.railway.app)**

---

## 📖 Visão Geral do Jogo

Em **Detective AI**, você assume o papel de um investigador responsável por solucionar crimes complexos. O jogo combina mecânicas clássicas de *detective adventure* com a flexibilidade de modelos de linguagem natural (LLMs).

### Principais Mecânicas:
1. **Interrogatório Dinâmico com IA:**
   - Converse livremente em linguagem natural com cada suspeito.
   - Os suspeitos não são meros chatbots genéricos: possuem personalidade, estado emocional (`patience`, `pressure`, `rapport`), postura psicológica (`neutral`, `defensive`, `pressured`, `cooperative`) e uma linha temporal estrita de fatos.
2. **Proteção Contra Alucinações & Spoiler Leak:**
   - O backend controla estritamente a verdade do jogo. O LLM nunca recebe segredos ou informações que o suspeito ainda não tenha sido forçado a admitir pela dinâmica do interrogatório.
3. **Quebra de Mentiras & Claims:**
   - Apresente evidências durante a conversa para confrontar inconsistências.
   - Quando confrontado com a evidência correta no momento certo, o suspeito quebra a mentira (`broken_claims`) e é forçado a recuar, ajustando sua postura e abrindo novas linhas de investigação.
4. **Dossiê do Caso (`Case File`):**
   - Suas descobertas alimentam automaticamente um dossiê com fatos revelados, contradições desmascaradas e pistas de motivo.
5. **Julgamento & Veredito Final:**
   - Ao se sentir pronto, acuse o suspeito principal, selecione as evidências de suporte e indique o motivo do crime. O motor avalia sua teoria contra a verdade objetiva do caso (`correct`, `partial` ou `wrong`).
6. **Gestão e Retomada de Sessões:**
   - Tela dedicada para consultar investigações anteriores, acompanhar status e retomar casos ativos de onde parou.
   - Resiliência integrada com recuperação amigável de sessão em caso de desconexão.

---

## 🏗️ Arquitetura do Sistema

```
                      +------------------------------------+
                      |    Frontend (Single Page Web App)  |
                      |    HTML5 / Modern CSS / Vanilla JS |
                      +-----------------+------------------+
                                        | HTTP / JSON
                                        v
                      +-----------------+------------------+
                      |         FastAPI REST API           |
                      |   (app/api/sessions, scenarios)    |
                      +-----------------+------------------+
                                        |
                 +----------------------+----------------------+
                 |                                             |
                 v                                             v
  +--------------+--------------+             +----------------+----------------+
  |    Interrogation Engine     |             |      AI / Prompt Pipeline       |
  | - Move Classifier           |             | - Prompt Builder                |
  | - Topic State Tracking      |             | - Response Render Context       |
  | - Claim Resolution          |             | - OpenAI Adapter (gpt-5-mini)   |
  | - Secret & Reveal Policies  |             | - Fallback & Response Guard     |
  | - Suspect Psychological FSM |             +---------------------------------+
  +--------------+--------------+                              |
                 |                                             |
                 +----------------------+----------------------+
                                        |
                                        v
                      +-----------------+------------------+
                      |   SQLite / SQLAlchemy Async/Sync   |
                      |  (game.db - Cenários, Sessões,     |
                      |   Mensagens, Estados de Suspeitos) |
                      +------------------------------------+
```

- **Backend:** FastAPI (Python 3.12/3.13) com arquitetura em camadas (`api`, `core`, `domain`, `infra`, `services`).
- **Persistência:** PostgreSQL gerenciado em produção no Railway (com volume persistente de 5 GB, imune a reinicializações) e SQLite local (`game.db`) via SQLAlchemy ORM.
- **Integração IA:** OpenAI Responses API (`gpt-5-mini`) com fallback automático para modo determinístico (`dummy`).
- **Frontend:** SPA responsivo e sem dependências pesadas, empacotado em arquivo único em `frontend/index.html` servido diretamente pelo FastAPI.

---

## 📁 Estrutura de Diretórios

```
detective_ai/
├── app/
│   ├── api/                  # Endpoints REST e schemas Pydantic
│   │   ├── routes: sessions.py, scenarios.py
│   │   └── schemas: case_file.py, chat.py, render_context.py, etc.
│   ├── core/                 # Configurações globais (Settings), exceções e handlers
│   ├── domain/               # Modelos de domínio puro (memória narrativa, regras)
│   ├── infra/                # Engine SQLAlchemy (PostgreSQL / SQLite), sessões e modelos
│   ├── services/             # Regras de negócio e motores:
│   │   ├── interrogation_turn_service.py   # Orquestrador atômico do turno
│   │   ├── prompt_builder.py               # Montagem de prompts isolados para IA
│   │   ├── claim_resolution_service.py     # Resolução de quebra de mentiras
│   │   ├── ai_adapter_openai.py            # Adaptador de integração com a OpenAI
│   │   ├── verdict_service.py              # Cálculo de veredito da acusação
│   │   └── ...                             # Serviços de tópicos, segredos, etc.
│   └── main.py               # Ponto de entrada FastAPI e montagem do frontend
├── docs/                     # Documentação aprofundada de arquitetura, API e cenários
├── frontend/
│   └── index.html            # Interface gráfica web completa do jogo
├── scenarios/
│   └── piloto.json           # Cenário inicial: "O Caso do Escritório Trancado"
├── scripts/                  # Scripts de utilidade e testes de simulação
├── tests/                    # 328+ testes automatizados (unitários, integração e E2E)
├── Procfile                  # Comando de execução web para Nixpacks/Railway
├── railway.json              # Configurações de deploy no Railway
└── requirements.txt          # Dependências do projeto
```

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.12 ou superior instalado.
- Conta e chave de API da OpenAI (opcional, pode-se usar o modo `dummy`).

### 1. Clonar o repositório
```bash
git clone https://github.com/ataidefilipe/detectiveai.git
cd detectiveai
```

### 2. Criar e ativar ambiente virtual
No Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

No Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
Copie o arquivo de exemplo `.env.example` para `.env`:
```bash
cp .env.example .env
```
Edite o arquivo `.env` e preencha sua `OPENAI_API_KEY`:
```ini
OPENAI_API_KEY=sk-proj-sua-chave-aqui
NPC_AI_PROVIDER=openai
OPENAI_MODEL=gpt-5-mini
```
*(Se preferir testar sem gastar tokens da OpenAI, basta definir `NPC_AI_PROVIDER=dummy`)*.

### 5. Iniciar o servidor
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Acessar o jogo
Abra seu navegador em:
- **Jogo / Interface Web:** [http://localhost:8000](http://localhost:8000)
- **Documentação Swagger da API:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Testes Automatizados

O projeto possui uma cobertura extensiva com **328 testes automatizados** validando regras de negócio, quebras de alegações, privacidade de segredos e fluxos de vitória.

Para rodar a suíte completa de testes:
```bash
pytest
```

Para rodar com verbosidade:
```bash
pytest -v
```

---

## 📚 Documentação Adicional

Aprofunde-se nos detalhes de engenharia e regras de design do projeto:

- 📐 **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Arquitetura de software, ciclo de vida dos NPCs e máquinas de estado.
- 🔌 **[docs/API.md](docs/API.md)** — Documentação completa das rotas HTTP, contratos de payload e respostas.
- 🚀 **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Guia de deploy em nuvem com Railway e Nixpacks.
- 📜 **[docs/scenario_schema.md](docs/scenario_schema.md)** — Especificação e guia para criação de novos casos e cenários investigativos.
- 🎭 **[docs/interrogatorio_ux.md](docs/interrogatorio_ux.md)** — Matriz de experiência do usuário e psicologia de interrogatório.
- 🤖 **[AGENT_GUIDELINES.md](AGENT_GUIDELINES.md)** — Guia de diretrizes para desenvolvedores e agentes autônomos.

---

## ⚖️ Licença

Projeto desenvolvido para fins educacionais, experimentais e de entretenimento com Inteligência Artificial. Todos os direitos reservados.
