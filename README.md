# Siren

Minimal Python debug helper with automatic cleanup.

> A tiny debugging utility for Python that prints variables with file/line context, traces function calls, measures execution time, and safely removes debug calls from your code.

[![PyPI - Version](https://img.shields.io/pypi/v/siren-debug?label=PyPI&color=blue)](https://pypi.org/project/siren-debug/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/siren-debug?label=Python)](https://pypi.org/project/siren-debug/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Install

```bash
pip install siren-debug
```

The package also installs two commands: `siren-clean` (remove debug calls) and `siren-autoload` (use `siren` without importing it).

---

## Quick Start

```python
from siren import siren

x = 10
user = {"name": "Alex", "items": [1, 2, 3]}

siren(x)
siren(user)
```

```text
[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN core.py:11] user = {'name': 'Alex', 'items': [1, 2, 3]}
```

Siren automatically uses `pprint` for complex objects, and picks up the file/line it was called from.

---

## Features

- Works with Python 2.7 and 3.6+
- Zero external dependencies
- Prints values with file and line number
- Uses `pprint` automatically for complex data
- Function tracing with `@siren.trace`, object diffing with `siren.diff`, and an interactive `siren.breakpoint()`
- Quiet mode, conditional logging, and file logging
- Removes `siren(...)` calls automatically with `siren-clean`
- Use `siren` anywhere without importing it via `siren-autoload`
- Works in scripts, CLI tools, Django, Flask, FastAPI, and more
- Colored output with emoji for easy visual scanning

---

## Usage

Call `siren(...)` with one or more values. It returns them unchanged, so it can be inlined:

```python
from siren import siren

siren(x, data, user)
result = siren(compute())  # still returns compute()'s value
```

**Label** — tag a call for easier scanning:

```python
siren(value, label="BEFORE SAVE")
```

**Timer** — measure execution time for a call:

```python
siren(x, timeit=True)
# [🧜‍ SIREN core.py:10] x = 10
# [🧜‍ SIREN TIME] 0.000123s
```

**Quiet mode** — suppress output without removing the call:

```python
siren(x, quiet=True)      # this call only, still returns x
siren.set_quiet(True)     # every call, until set_quiet(False)
```

**Conditional logging** — only print when a condition holds:

```python
siren(x, if_equals=5)        # only if x == 5
siren(items, if_len_gt=100)  # only if len(items) > 100
siren(items, if_len_lt=5)    # only if len(items) < 5
siren(result, if_true=True)  # only if result is truthy
siren(error, if_false=True)  # only if error is falsy
```

**Logging to file** — mirror output to a file:

```python
siren.set_logfile("debug.log")
siren(x)  # prints to stdout AND writes to debug.log
```

**Inspect configuration**:

```python
config = siren.get_config()
print(config)  # {"quiet": False, "logfile": None, "enabled": True}
```

---

## Function tracing

`@siren.trace` logs a function's calls, arguments, return value, execution time, and exceptions automatically:

```python
from siren import trace

@siren.trace
def add(a, b):
    return a + b

add(2, 3)
```

```text
[🧜‍ SIREN core.py:10] Calling add(a=2, b=3)
[🧜‍ SIREN core.py:11] Returned from add -> 5 [int] (0.000123s)
```

Configuration options (all default to `True`):

| Option | Effect |
|---|---|
| `timeit` | Show execution time |
| `show_args` | Show function arguments |
| `show_return` | Show return value |
| `show_type` | Show return type in brackets |

```python
@siren.trace(timeit=True, show_args=False, show_type=False)
def multiply(a, b):
    return a * b
```

Exceptions are logged before being re-raised, so `@siren.trace` never swallows an error:

```python
@siren.trace
def divide(a, b):
    return a / b

divide(5, 0)  # Logs exception before raising
```

---

## Diff and breakpoint

**`siren.diff`** compares two dicts, lists, tuples, or any comparable objects:

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

**`siren.breakpoint()`** pauses execution and prints local variables:

```python
x = 42
data = {"items": [1, 2, 3]}

siren.breakpoint()  # Pauses and displays all locals
# Press Ctrl+C to continue, or type 'd' to drop into pdb
```

---

## Cleaning debug calls

Run `siren-clean` in a project folder to remove all `siren(...)` calls and their import lines — comments and string literals are left untouched:

```bash
siren-clean
```

Before:

```python
from siren import siren
siren(x)
print("hello")
siren(data)
```

After:

```python
print("hello")
```

---

## Autoload (no per-file imports)

By default you still need `from siren import siren` in every file that uses it. If you'd rather call `siren(x)` anywhere in a project without importing it each time, enable autoload once per environment (virtualenv, Docker image, CI job, etc.):

```bash
siren-autoload on
siren-autoload status   # check whether it's enabled
siren-autoload off      # disable again
```

This writes a `.pth` file into the current environment's `site-packages`, injecting `siren` into Python's builtins as soon as any interpreter starts in that environment — no import needed anywhere, including in Django apps, Flask views, scripts, or the shell. It's opt-in per environment, so it won't silently affect environments where you didn't run `on`.

---

## Framework examples

<details>
<summary>Django</summary>

```python
from django.http import JsonResponse
from siren import siren

def my_view(request):
    user_data = request.GET.dict()
    siren(user_data, label="REQUEST_PARAMS")

    result = process_data(user_data)
    siren(result)

    return JsonResponse(result)
```
</details>

<details>
<summary>Flask</summary>

```python
from flask import Flask, request
from siren import siren, trace

app = Flask(__name__)

@app.route("/api/users")
def get_users():
    query = request.args.get("q")
    siren(query, label="SEARCH_QUERY")

    users = search_users(query)
    return {"users": users}

@siren.trace
def search_users(query):
    # Function entry/exit will be logged automatically
    return [{"id": 1, "name": "Alice"}]
```
</details>

<details>
<summary>FastAPI</summary>

```python
from fastapi import FastAPI
from siren import siren, trace

app = FastAPI()

@app.get("/items/{item_id}")
async def get_item(item_id: int, q: str = None):
    siren({"item_id": item_id, "q": q}, label="QUERY_PARAMS")

    item = await fetch_item(item_id)
    return item

@siren.trace(timeit=True)
async def fetch_item(item_id: int):
    # Execution time and arguments will be logged
    return {"id": item_id, "name": "Item"}
```
</details>

---

## Why use Siren?

Debug prints are easy to add, but hard to remove later. Siren gives you a fast debug workflow and a safe cleanup step so your temporary debug code does not stay in production.

---

## Project

- Package name: `siren-debug`
- Python versions: `2.7`, `3.6+`
- License: MIT
- PyPI: https://pypi.org/project/siren-debug/

## License

MIT
