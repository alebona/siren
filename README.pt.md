# Siren

Ferramenta mínima de debug para Python com limpeza automática.

> Um utilitário leve para depurar variáveis com contexto de arquivo/linha, rastrear chamadas de função, medir tempo de execução e remover chamadas de debug do código.

[![PyPI - Version](https://img.shields.io/pypi/v/siren-debug?label=PyPI&color=blue)](https://pypi.org/project/siren-debug/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/siren-debug?label=Python)](https://pypi.org/project/siren-debug/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Instalação

```bash
pip install siren-debug
```

O pacote também instala dois comandos: `siren-clean` (remove chamadas de debug) e `siren-autoload` (usa `siren` sem precisar importar).

---

## Começando

```python
from siren import siren

x = 10
user = {"nome": "Alex", "itens": [1, 2, 3]}

siren(x)
siren(user)
```

```text
[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN core.py:11] user = {'nome': 'Alex', 'itens': [1, 2, 3]}
```

Siren usa `pprint` automaticamente para objetos complexos, e identifica sozinho o arquivo/linha de onde foi chamado.

---

## Funcionalidades

- Funciona com Python 2.7 e 3.6+
- Sem dependências externas
- Exibe valores com arquivo e número da linha
- Usa `pprint` automaticamente para objetos complexos
- Trace de função com `@siren.trace`, diff de objetos com `siren.diff`, breakpoint interativo com `siren.breakpoint()`, snapshot de memória com `siren.memory()`, e captura de traceback colorido com `siren.catch`
- Modo silencioso, logging condicional e logging em arquivo
- Remove chamadas `siren(...)` automaticamente com `siren-clean`
- Use `siren` em qualquer lugar sem importar via `siren-autoload`
- Scaffolding de projeto/arquivo com `siren-scaffold`, verificação de `.env` com `siren-env`
- Gerenciador de snippets no terminal (`siren-snippet`) e cliente HTTP sem dependências (`siren-http`)
- Checagens locais de qualidade de código com `siren-quality` (código morto, lint, complexidade ciclomática)
- Funciona em scripts, CLI, Django, Flask, FastAPI e mais
- Saída colorida com emoji para facilitar a leitura

---

## Uso

Chame `siren(...)` com um ou mais valores. Ele retorna os valores sem alterá-los, então pode ser usado inline:

```python
from siren import siren

siren(x, data, user)
resultado = siren(computar())  # ainda retorna o valor de computar()
```

**Rótulo (label)** — marque uma chamada para facilitar a leitura:

```python
siren(value, label="ANTES DO SAVE")
```

**Timer** — meça o tempo de execução de uma chamada:

```python
siren(x, timeit=True)
# [🧜‍ SIREN core.py:10] x = 10
# [🧜‍ SIREN TIME] 0.000123s
```

**Modo silencioso** — suprime a saída sem remover a chamada:

```python
siren(x, quiet=True)      # só essa chamada, ainda retorna x
siren.set_quiet(True)     # toda chamada, até set_quiet(False)
```

**Logging condicional** — só imprime quando uma condição é satisfeita:

```python
siren(x, if_equals=5)        # só se x == 5
siren(items, if_len_gt=100)  # só se len(items) > 100
siren(items, if_len_lt=5)    # só se len(items) < 5
siren(result, if_true=True)  # só se result for verdadeiro
siren(error, if_false=True)  # só se error for falso
```

**Logging em arquivo** — espelha a saída para um arquivo:

```python
siren.set_logfile("debug.log")
siren(x)  # imprime no stdout E escreve em debug.log
```

**Verificar configuração**:

```python
config = siren.get_config()
print(config)  # {"quiet": False, "logfile": None, "enabled": True}
```

---

## Trace de função

`@siren.trace` registra automaticamente as chamadas, argumentos, retorno, tempo de execução e exceções de uma função:

```python
from siren import trace

@siren.trace
def soma(a, b):
    return a + b

soma(2, 3)
```

```text
[🧜‍ SIREN core.py:10] Calling soma(a=2, b=3)
[🧜‍ SIREN core.py:11] Returned from soma -> 5 [int] (0.000123s)
```

Opções de configuração (todas com padrão `True`):

| Opção | Efeito |
|---|---|
| `timeit` | Exibe tempo de execução |
| `show_args` | Exibe argumentos da função |
| `show_return` | Exibe valor de retorno |
| `show_type` | Exibe tipo do retorno entre colchetes |

```python
@siren.trace(timeit=True, show_args=False, show_type=False)
def multiplica(a, b):
    return a * b
```

Exceções são registradas antes de serem relançadas, então `@siren.trace` nunca engole um erro:

```python
@siren.trace
def divide(a, b):
    return a / b

divide(5, 0)  # Registra exceção antes de lançar
```

---

## Diff, breakpoint, memória e catch

**`siren.diff`** compara dois dicts, listas, tuplas ou qualquer objeto comparável:

```python
before = {"name": "Alice", "age": 30}
after = {"name": "Alice", "age": 31, "city": "NYC"}

siren.diff(before, after)
```

```text
[🧜‍ SIREN test.py:10] DIFF
[🧜‍ SIREN test.py:11] [~] age: 30 → 31 (changed)
[🧜‍ SIREN test.py:12] [+] city: NYC (new)
```

**`siren.breakpoint()`** pausa a execução e exibe as variáveis locais:

```python
x = 42
data = {"items": [1, 2, 3]}

siren.breakpoint()  # Pausa e exibe todos os locais
# Pressione Ctrl+C para continuar, ou digite 'd' para entrar no pdb
```

**`siren.memory()`** exibe o uso de memória atual/pico rastreado (requer Python 3.4+; no Python 2 exibe uma mensagem clara em vez de falhar):

```python
siren.memory()          # [🧜‍ SIREN MEMORY ...] current=1.2MB peak=1.5MB
siren.memory(top=5)     # também exibe os 5 principais pontos de alocação
```

**`siren.catch`** é um context manager que exibe um traceback colorido em caso de exceção e relança o erro — nunca engole exceções:

```python
with siren.catch():
    chamada_arriscada()
```

---

## Limpeza de chamadas de debug

Execute `siren-clean` na pasta do projeto para remover todas as chamadas `siren(...)` e seus imports — comentários e literais de string são preservados:

```bash
siren-clean
```

Antes:

```python
from siren import siren
siren(x)
print("hello")
siren(data)
```

Depois:

```python
print("hello")
```

---

## Autoload (sem import em cada arquivo)

Por padrão ainda é preciso `from siren import siren` em cada arquivo que usa a ferramenta. Se preferir chamar `siren(x)` em qualquer lugar do projeto sem importar toda vez, ative o autoload uma vez por ambiente (virtualenv, imagem Docker, job de CI, etc.):

```bash
siren-autoload on
siren-autoload status   # verifica se está ativado
siren-autoload off      # desativa novamente
```

Isso escreve um arquivo `.pth` no `site-packages` do ambiente atual, injetando `siren` nos builtins do Python assim que qualquer interpretador inicia nesse ambiente — sem import em lugar nenhum, incluindo apps Django, views Flask, scripts ou o shell. Como é opt-in por ambiente, não afeta silenciosamente ambientes onde você não rodou o `on`.

---

## Além do debug

O siren também traz algumas ferramentas de CLI pequenas e sem dependências pro dia a dia do projeto.

### Scaffolding — `siren-scaffold`

Gera um esqueleto de arquivo ou projeto:

```bash
siren-scaffold script my_tool       # um script único com guarda main()
siren-scaffold package my_package   # um diretório de pacote com __init__.py, core.py e tests/
siren-scaffold class Widget         # uma classe simples
siren-scaffold dataclass Point      # um value object em Python puro (sem precisar do módulo dataclasses)
siren-scaffold test Widget          # um stub de unittest.TestCase
```

Ele se recusa a sobrescrever arquivos existentes.

### Verificação de `.env` — `siren-env`

```bash
siren-env diff                                    # compara .env.example com .env
siren-env diff --example .env.sample --env .env.local
```

Reporta chaves presentes em um arquivo e ausentes no outro, e sai com código de erro em caso de divergência — dá pra usar como checagem de CI.

### Snippets — `siren-snippet`

```bash
echo "print('ola')" | siren-snippet save saudacao --tag python
siren-snippet save query --file query.sql --tag sql   # a partir de um arquivo, em vez de stdin
siren-snippet show saudacao
siren-snippet copy saudacao                            # copia direto pra área de transferência
siren-snippet edit saudacao                             # abre no seu $EDITOR
siren-snippet rename saudacao ola
siren-snippet list [--tag sql]
siren-snippet tags                                      # toda tag em uso, com contagem
siren-snippet search select                              # busca por nome, tag ou conteúdo
siren-snippet remove saudacao
```

`save` recusa sobrescrever um snippet existente a menos que você passe `--force` — vale o mesmo pro `rename`.

Snippets podem ter marcadores `{{placeholder}}`, preenchidos na hora de usar em vez de na hora de salvar:

```bash
echo 'SELECT * FROM {{tabela}};' | siren-snippet save query --tag sql
siren-snippet copy query --var tabela=usuarios   # copia "SELECT * FROM usuarios;"
siren-snippet show query --var tabela=usuarios   # mesma coisa, mas impresso em vez de copiado
```

Faça backup ou mova seus snippets entre máquinas com `export`/`import` (conteúdo, tags e datas viajam juntos; `import` pula nomes que já existem a menos que você passe `--force`):

```bash
siren-snippet export backup.json
siren-snippet import backup.json
```

Snippets são salvos como arquivos de texto simples em `~/.siren/snippets/`, com tags/datas guardadas separadamente em `~/.siren/snippets/_index.json` (então qualquer snippet salvo antes dessa funcionalidade existir continua funcionando normalmente, só sem tags).

### Cliente HTTP — `siren-http`

Um cliente leve tipo httpie, construído só com `urllib`:

```bash
siren-http GET https://api.example.com/items
siren-http POST https://api.example.com/items --json '{"name": "x"}' -H "Authorization: Bearer TOKEN"
siren-http GET https://api.example.com/items --save minha-requisicao   # salva como collection local
siren-http replay minha-requisicao                                     # reenvia uma requisição salva
siren-http list                                                        # lista requisições salvas
```

Também dá pra logar automaticamente toda chamada HTTP feita pelo seu próprio código via `requests` ou `httpx`, sem tocar nesse código — `requests`/`httpx` não são dependências do siren, só são importados quando você chama isso:

```python
siren.patch_requests()    # toda chamada requests.Session passa a logar método/url/status/duração
siren.patch_httpx()       # o mesmo, para httpx.Client (só síncrono)
siren.unpatch_requests()
siren.unpatch_httpx()
```

### Qualidade de código — `siren-quality`

Checagens locais construídas sobre o módulo `ast` da stdlib (sem depender de pyflakes/radon/etc):

```bash
siren-quality deadcode .     # imports não usados e defs de módulo nunca referenciadas no mesmo arquivo
siren-quality lint .         # `except:` genérico, pdb.set_trace()/breakpoint() esquecidos, comentários TODO/FIXME
siren-quality complexity .   # complexidade ciclomática por função, sinaliza acima de --threshold (padrão 10)
```

`deadcode` é uma heurística restrita ao próprio arquivo — não enxerga uso vindo de outros arquivos, então trate os achados como candidatos a conferir, não certezas.

---

## Tier pro

Tudo acima é grátis e roda 100% offline. O pacote `siren-debug` também traz alguns comandos do tier pago, que conversam com um backend pequeno (repositório separado, código fechado) pra uma feature paga: captura de exceções com histórico pesquisável, em vez de só o `siren.catch()` local.

```bash
siren-login signup voce@exemplo.com   # cria uma conta + chave de API, salva em ~/.siren/credentials.json
siren-login status                     # verifica seu plano/licença
siren-login logout
```

```python
try:
    risky()
except Exception:
    siren.report()   # envia a exceção (com traceback) pro seu workspace
```

```bash
siren-events list        # exceções recentes reportadas de qualquer uma das suas máquinas
siren-events show <id>   # traceback completo de uma delas
```

`siren.report()` nunca lança erro por conta própria — se você não estiver logado, ou o backend não estiver acessível, ele imprime uma mensagem e retorna `None` em vez de quebrar seu tratamento de erro. Aponte o CLI pra um backend diferente com `SIREN_API_URL` (padrão `http://127.0.0.1:8000`, já que o backend hospedado ainda não está disponível publicamente).

---

## Exemplos com frameworks

<details>
<summary>Django</summary>

```python
from django.http import JsonResponse
from siren import siren

def minha_view(request):
    dados_usuario = request.GET.dict()
    siren(dados_usuario, label="REQUEST_PARAMS")

    resultado = processar_dados(dados_usuario)
    siren(resultado)

    return JsonResponse(resultado)
```
</details>

<details>
<summary>Flask</summary>

```python
from flask import Flask, request
from siren import siren, trace

app = Flask(__name__)

@app.route("/api/usuarios")
def listar_usuarios():
    query = request.args.get("q")
    siren(query, label="SEARCH_QUERY")

    usuarios = buscar_usuarios(query)
    return {"usuarios": usuarios}

@siren.trace
def buscar_usuarios(query):
    # Entrada/saída de função será registrada automaticamente
    return [{"id": 1, "nome": "Alice"}]
```
</details>

<details>
<summary>FastAPI</summary>

```python
from fastapi import FastAPI
from siren import siren, trace

app = FastAPI()

@app.get("/items/{item_id}")
async def obter_item(item_id: int, q: str = None):
    siren({"item_id": item_id, "q": q}, label="QUERY_PARAMS")

    item = await buscar_item(item_id)
    return item

@siren.trace(timeit=True)
async def buscar_item(item_id: int):
    # Tempo de execução e argumentos serão registrados
    return {"id": item_id, "nome": "Item"}
```
</details>

---

## Por que usar Siren?

Imprimir valores para debugar é rápido, mas remover esses prints depois é trabalhoso. Siren oferece um fluxo de debug rápido e uma limpeza segura para que código temporário não fique em produção.

---

## Projeto

- Nome do pacote: `siren-debug`
- Versões Python: `2.7`, `3.6+`
- Licença: MIT
- PyPI: https://pypi.org/project/siren-debug/

## Licença

MIT
