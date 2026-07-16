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

The package also installs a cleanup command:

```bash
siren-clean
```

---

## Quick Start

```python
from siren import siren

x = 10
user = {"name": "Alex", "items": [1, 2, 3]}

siren(x)
siren(user)
```

Example output:

```text
[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN core.py:11] user = {'name': 'Alex', 'items': [1, 2, 3]}
```

Siren automatically uses `pprint` for complex objects.

---

## Features

- Works with Python 3+
- Zero external dependencies
- Prints values with file and line number
- Uses `pprint` automatically for complex data
- Optional execution timer with `timeit=True`
- Function tracing with `@siren.trace`
- Removes `siren(...)` calls automatically
- Safe cleanup using Python `tokenize`
- Works in scripts, CLI tools, Django, Flask, FastAPI, and more
- Colored output with emoji for easy visual scanning

---

## Usage

Import the helper and call it with one or more values:

```python
from siren import siren

siren(x, data, user)
```

You can also add a custom label:

```python
siren(value, label="BEFORE SAVE")
```

---

## Timer

Enable timing for a single call:

```python
siren(x, timeit=True)
```

Output example:

```text
[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN TIME] 0.000123s
```

---

## Function tracing

Use the trace decorator to log calls, arguments, return values, execution time, and exceptions:

```python
from siren import trace

@siren.trace
def add(a, b):
    return a + b

add(2, 3)
```

Example output:

```text
[🧜‍ SIREN core.py:10] Calling add(a=2, b=3)
[🧜‍ SIREN core.py:11] Returned from add -> 5 [int] (0.000123s)
```

Configuration options:

- `timeit=True` – Display execution time (default: True)
- `show_args=True` – Display function arguments (default: True)
- `show_return=True` – Display return value (default: True)
- `show_type=True` – Display return type in brackets (default: True)

Example with options:

```python
@siren.trace(timeit=True, show_args=False, show_type=False)
def multiply(a, b):
    return a * b
```

The decorator also captures and logs exceptions:

```python
@siren.trace
def divide(a, b):
    return a / b

divide(5, 0)  # Logs exception before raising
```

---

## Cleaning debug calls

The package installs a command named `siren-clean`.
Run it in a project folder to remove all `siren(...)` calls and associated import lines:

```bash
siren-clean
```

Example:

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

The cleaner preserves comments and string literals.

---

## Autoload (no per-file imports)

By default you still need `from siren import siren` in every file that uses it. If you'd rather call `siren(x)` anywhere in a project without importing it each time, enable autoload once per environment (virtualenv, Docker image, CI job, etc.):

```bash
siren-autoload on
```

This writes a `.pth` file into the current environment's `site-packages`, so `siren` is injected into Python's builtins as soon as any interpreter starts in that environment — no import needed anywhere, including in Django apps, Flask views, scripts, or the shell.

```bash
siren-autoload status   # check whether it's enabled
siren-autoload off      # disable again
```

Because it's opt-in per environment (nothing changes just from `pip install`), it won't silently affect environments where you didn't run `on`.

---

## Advanced Features

### Quiet mode (suppress output for specific calls)

```python
from siren import siren

siren(x, quiet=True)  # Won't print anything, but returns the value
```

### Global quiet mode

```python
from siren import siren

siren.set_quiet(True)   # Disable all siren output
siren.set_quiet(False)  # Enable again
```

### Logging to file

```python
from siren import siren

siren.set_logfile("debug.log")
siren(x)  # Prints to stdout AND writes to debug.log
```

### Conditional logging

Only print when specific conditions are met:

```python
from siren import siren

# Only print if value equals
siren(x, if_equals=5)

# Only print if length > N
siren(items, if_len_gt=100)

# Only print if length < N
siren(items, if_len_lt=5)

# Only print if truthy
siren(result, if_true=True)

# Only print if falsy
siren(error, if_false=True)
```

### Diff objects

Compare two objects and display differences:

```python
from siren import siren

before = {"name": "Alice", "age": 30}
after = {"name": "Alice", "age": 31, "city": "NYC"}

siren.diff(before, after)
```

Output:

```text
[🧜‍ SIREN test.py:10] DIFF
[🧜‍ SIREN test.py:11] [~] age: 30 → 31 (changed)
[🧜‍ SIREN test.py:12] [+] city: NYC (new)
```

Works with dicts, lists, tuples, and any comparable objects.

### Interactive breakpoint

Pause execution and inspect local variables:

```python
from siren import siren

x = 42
data = {"items": [1, 2, 3]}

siren.breakpoint()  # Pauses and displays all locals
# Press Ctrl+C to continue
# Type 'd' to enter debugger (pdb)
```

Output:

```text
[🧜‍ SIREN test.py:10] BREAKPOINT
[🧜‍ SIREN test.py:11] === BREAKPOINT ===
[🧜‍ SIREN test.py:12] Locals:
[🧜‍ SIREN test.py:13]   x = 42
[🧜‍ SIREN test.py:14]   data = {'items': [1, 2, 3]}
```

### Check configuration

```python
from siren import siren

config = siren.get_config()
print(config)  # {"quiet": False, "logfile": None, "enabled": True}
```

---

## Examples with Frameworks

### Django

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

### Flask

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

### FastAPI

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

---

## Why use Siren?

Debug prints are easy to add, but hard to remove later. Siren gives you a fast debug workflow and a safe cleanup step so your temporary debug code does not stay in production.

---

## Project

- Package name: `siren-debug`
- Python versions: `>=3.6`
- License: MIT
- PyPI: https://pypi.org/project/siren-debug/

---

## License

MIT