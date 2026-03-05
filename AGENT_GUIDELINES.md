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
