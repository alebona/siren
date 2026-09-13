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
- Trace de função com `@siren.trace`, diff de objetos com `siren.diff`, e breakpoint interativo com `siren.breakpoint()`
- Modo silencioso, logging condicional e logging em arquivo
- Remove chamadas `siren(...)` automaticamente com `siren-clean`
- Use `siren` em qualquer lugar sem importar via `siren-autoload`
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

## Diff e breakpoint

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
