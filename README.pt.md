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

O pacote também instala o comando de limpeza:

```bash
siren-clean
```

---

## Começando

```python
from siren import siren

x = 10
user = {"nome": "Alex", "itens": [1, 2, 3]}

siren(x)
siren(user)
```

Exemplo de saída:

```text
[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN core.py:11] user = {'nome': 'Alex', 'itens': [1, 2, 3]}
```

Siren usa `pprint` automaticamente para objetos complexos.

---

## Funcionalidades

- Funciona com Python 3+
- Sem dependências externas
- Exibe valores com arquivo e número da linha
- Usa `pprint` para objetos complexos
- Timer opcional com `timeit=True`
- Trace decorator com `@siren.trace`
- Remove chamadas `siren(...)` automaticamente
- Limpeza segura usando `tokenize` do Python
- Funciona em scripts, CLI, Django, Flask, FastAPI e mais
- Saída colorida com emoji para facilitar a leitura

---

## Uso

Importe e chame com um ou mais valores:

```python
from siren import siren

siren(x, data, user)
```

Também é possível adicionar um rótulo personalizado:

```python
siren(value, label="ANTES DO SAVE")
```

---

## Timer

Ative a medição de tempo em uma chamada:

```python
siren(x, timeit=True)
```

Saída exemplo:

```text
[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN TIME] 0.000123s
```

---

## Trace de função

Use o decorator para registrar chamadas, argumentos, retornos, tempo de execução e exceções:

```python
from siren import trace

@siren.trace
def soma(a, b):
    return a + b

soma(2, 3)
```

Exemplo de saída:

```text
[🧜‍ SIREN core.py:10] Calling soma(a=2, b=3)
[🧜‍ SIREN core.py:11] Returned from soma -> 5 [int] (0.000123s)
```

Opções de configuração:

- `timeit=True` – Exibe tempo de execução (padrão: True)
- `show_args=True` – Exibe argumentos (padrão: True)
- `show_return=True` – Exibe retorno (padrão: True)
- `show_type=True` – Exibe tipo do retorno entre colchetes (padrão: True)

Exemplo com opções:

```python
@siren.trace(timeit=True, show_args=False, show_type=False)
def multiplica(a, b):
    return a * b
```

O decorator também captura e registra exceções:

```python
@siren.trace
def divide(a, b):
    return a / b

divide(5, 0)  # Registra exceção antes de lançar
```

---

## Limpeza de chamadas de debug

O pacote instala o comando `siren-clean`.
Execute-o na pasta do projeto para remover todas as chamadas `siren(...)` e imports relacionados:

```bash
siren-clean
```

Exemplo:

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

O cleaner preserva comentários e literais de string.

---

## Autoload (sem import em cada arquivo)

Por padrão ainda é preciso `from siren import siren` em cada arquivo que usa a ferramenta. Se preferir chamar `siren(x)` em qualquer lugar do projeto sem importar toda vez, ative o autoload uma vez por ambiente (virtualenv, imagem Docker, job de CI, etc.):

```bash
siren-autoload on
```

Isso escreve um arquivo `.pth` no `site-packages` do ambiente atual, injetando `siren` nos builtins do Python assim que qualquer interpretador inicia nesse ambiente — sem import em lugar nenhum, incluindo apps Django, views Flask, scripts ou o shell.

```bash
siren-autoload status   # verifica se está ativado
siren-autoload off      # desativa novamente
```

Como é opt-in por ambiente (nada muda só com o `pip install`), não afeta silenciosamente ambientes onde você não rodou o `on`.

---

## Recursos Avançados

### Modo silencioso (silenciar output de chamadas específicas)

```python
from siren import siren

siren(x, quiet=True)  # Não vai imprimir, mas retorna o valor
```

### Modo silencioso global

```python
from siren import siren

siren.set_quiet(True)   # Desabilita todo output do siren
siren.set_quiet(False)  # Habilita novamente
```

### Logging em arquivo

```python
from siren import siren

siren.set_logfile("debug.log")
siren(x)  # Imprime no stdout E escreve em debug.log
```

### Logging condicional

Imprima apenas quando condições específicas são atendidas:

```python
from siren import siren

# Só imprime se valor é igual
siren(x, if_equals=5)

# Só imprime se tamanho > N
siren(items, if_len_gt=100)

# Só imprime se tamanho < N
siren(items, if_len_lt=5)

# Só imprime se valor é verdadeiro
siren(result, if_true=True)

# Só imprime se valor é falso
siren(error, if_false=True)
```

### Comparar objetos (Diff)

Compare dois objetos e veja as diferenças:

```python
from siren import siren

before = {"name": "Alice", "age": 30}
after = {"name": "Alice", "age": 31, "city": "NYC"}

siren.diff(before, after)
```

Saída:

```text
[🧜‍ SIREN test.py:10] DIFF
[🧜‍ SIREN test.py:11] [~] age: 30 → 31 (changed)
[🧜‍ SIREN test.py:12] [+] city: NYC (new)
```

Funciona com dicts, listas, tuplas e qualquer objeto comparável.

### Breakpoint interativo

Pausa a execução e inspeciona variáveis locais:

```python
from siren import siren

x = 42
data = {"items": [1, 2, 3]}

siren.breakpoint()  # Pausa e exibe todos os locais
# Pressione Ctrl+C para continuar
# Digite 'd' para entrar no debugger (pdb)
```

Saída:

```text
[🧜‍ SIREN test.py:10] BREAKPOINT
[🧜‍ SIREN test.py:11] === BREAKPOINT ===
[🧜‍ SIREN test.py:12] Locals:
[🧜‍ SIREN test.py:13]   x = 42
[🧜‍ SIREN test.py:14]   data = {'items': [1, 2, 3]}
```

### Verificar configuração

```python
from siren import siren

config = siren.get_config()
print(config)  # {"quiet": False, "logfile": None, "enabled": True}
```

---

## Exemplos com Frameworks

### Django

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

### Flask

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

### FastAPI

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

---

## Por que usar Siren?

Imprimir valores para debugar é rápido, mas remover esses prints depois é trabalhoso. Siren oferece um fluxo de debug rápido e uma limpeza segura para que código temporário não fique em produção.

---

## Projeto

- Nome do pacote: `siren-debug`
- Versão Python: `>=3.6`
- Licença: MIT
- PyPI: https://pypi.org/project/siren-debug/

---

## Licença

MIT
