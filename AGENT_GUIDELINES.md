# AI Developer Guidelines & Project Knowledge Base

Este arquivo serve como uma base de conhecimento vivo e um guia de diretrizes para agentes de IA que trabalhem neste projeto. Ele documenta padrões arquiteturais, armadilhas comuns encontradas em desenvolvimentos anteriores, e regras de ambiente para evitar re-trabalho e erros repetitivos.

Por favor, atualize este arquivo sempre que um novo padrão for estabelecido ou um bug complexo/recorrente for resolvido.

---

## 1. Ambiente e Sistema Operacional (Windows/PowerShell)

* **Execução de Comandos CLI:** O usuário utiliza Windows com PowerShell.
    * **Evite `&&`:** Não encadeie comandos usando `&&` (ex: `cmd1 && cmd2`), pois o PowerShell não suporta este operador nativamente dessa forma em todas as versões. Utilize `;` (ponto e vírgula) para sequenciar a execução (ex: `git add .; git commit -m "msg"`).
    * **Criação de Arquivos via CLI:** Evite usar `echo. > arquivo` ou `touch`. Se precisar criar um arquivo via terminal, prefira comandos PowerShell como `New-Item -ItemType File -Force -Path caminho/do/arquivo` ou utilize a ferramenta de escrita de arquivos diretamente.

---

## 2. Testes Automatizados (Pytest)

### 2.1. Conexão e Inicialização do Banco de Dados (SQLite em Memória)
* **`OperationalError`:** Se um teste falhar com um erro operacional do banco de dados (ex: tabela não encontrada), verifique se você chamou a função inicializadora das tabelas.
* **Sempre inicialize as tabelas:** Nos arquivos de teste que instanciam um db de sessão limpo, garanta a chamada de `init_db()` (de `app.infra.db`) antes de instanciar a sessão (`SessionLocal()`).

### 2.2. Ciclo de Vida do Banco de Testes e Setup de Dados (Fixtures)
* Em `tests/conftest.py`, já existe uma fixture com `autouse=True` que realiza o truncamento/recriação de tabelas a cada teste para garantir isolamento.
* **Cuidado com Escopos de Fixture (`scope="session"`):** Se você popular o banco de dados dentro de uma fixture com `scope="session"`, essa inserção pode ser apagada pelas fixtures globais de recriação de tabela que rodam por teste. Prefira inserir/carregar os dados mockados no mesmo escopo da função de teste, no próprio corpo do teste, ou usando uma `yield` fixture padrão.

### 2.3. Resolução de Caminhos para Leitura de Arquivos
* **`FileNotFoundError`:** Ao carregar mockups ou jsons (como o `piloto.json`) dentro dos testes, jamais utilize caminhos relativos ao diretório de execução atual (cw), pois o teste pode rodar de pastas diferentes.
* **Sempre use caminhos relativos ao arquivo do teste:** 
  ```python
  import os
  scenario_path = os.path.join(os.path.dirname(__file__), "../../scenarios/piloto.json")
  ```
  Preste muita atenção ao número de saltos para trás (`../` ou `../../`) baseando-se em onde o teste está (ex: `tests/services/` precisa de `../../`).

---

## 3. Integração e Extensão de API (FastAPI)

### 3.1. Propagação de Novas Propriedades de Schema
* **O Efeito Cascata de Erros de Schema (`HTTP 422 Unprocessable Entity`):** Quando você adicionar um campo obrigatório a um schema de Request (ex: `AccuseRequest`), *todos* os testes unitários e, principalmente, End-to-End (`E2E`) que acionavam aquela rota começarão a falhar se não receberem a nova chave de payload. Sempre busque o endpoint globalmente na pasta `/tests` e atualize eventuais payloads defasados.

### 3.2. Repasse de Argumentos em Roteadores e Serviços
* Se você adicionar na casca da API o novo parâmetro do schema e enviá-lo para os serviços de negócios subjacentes, garanta a atualização da assinatura destas funções de serviço em cascata.
* **`TypeError: missing 1 required positional argument`:** Erro muito comum proveniente de atualizar o `controller` mas esquecer de atualizar as evocações do `finalize_session` (ou de outro serviço) com as novas chaves extraídas do Request Pydantic. Revisar sempre o fluxo: `Router -> Service Layer -> Infra/DB Layer`.

---

## 4. Evolução do Checklist

* Este é um documento vivo. Ao resolver problemas de compatibilidade difíceis ou notar que a IA bateu muita cabeça resolvendo o mesmo tipo de falha arquitetural, documente o aprendizado neste arquivo para a próxima iteração.

---

## 5. Mocks de Testes e Validação Pydantic

### 5.1. Cuidados ao Criar Mocks de JSON
* **`pydantic_core.ValidationError`**: Ao criar mocks manuais de dicionários JSON dentro dos testes (ex: para testar loaders de cenário), verifique sempre a estrutura exata do Schema alvo (em `schema_scenario.py` ou similares). É comum que as variáveis tenham nomes diferentes entre a representação de banco de dados e os contratos Pydantic (ex: `label` vs `name`). Um campo ausente ou com nome incorreto derrubará o teste na etapa de parse com erro obscuro. Sempre cruze a declaração de dict do mock com a definição Pydantic.

---

## 6. Mecânicas de Jogo e Narrativa (Gameplay)

### 6.1. Normalização de Nomes de Evidências em Mentiras
* **Mapeamento de Slug para Nome Amigável:** No banco de dados (`SuspectModel.lies`), o campo `broken_by_evidence` deve conter o *nome exibível* da evidência (ex: "Faca Suja") e não o identificador curto (slug) do JSON (ex: "faca_01"). O `scenario_loader.py` realiza essa tradução automaticamente.
* **Erro Comum em Testes Unitários:** Ao criar mentiras (`lies`) em mocks manuais para testes, garanta que o valor de `broken_by_evidence` corresponda EXATAMENTE ao atributo `.name` do objeto `EvidenceModel` persistido, sob o risco da mentira nunca ser detectada como quebrada pelo `lie_break_service.py`.

### 6.2. Quebra de Mentiras e Contexto de Tópicos
* **Dependência de Tópico:** Para que uma mentira seja quebrada, não basta apresentar a evidência correta; o jogador deve estar "falando" sobre o tópico associado àquela mentira (presente no `detected_topic_ids` da mensagem atual ou no `last_topic_id` da sessão). 
* **Teste de Integração:** Em testes que buscam validar a quebra de mentiras, certifique-se de que o texto da mensagem do jogador contenha palavras-chave que disparem a detecção do tópico correto, ou que o turno anterior tenha estabelecido esse tópico como o contexto ativo.

