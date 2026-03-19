# Siren

Minimalist debug tool for Python.

Siren is a lightweight alternative to `print` / `pprint`, designed to work  
with any Python 3 version and any framework like Django, Flask, FastAPI, or pure Python scripts.

The main goal of Siren is simple:

✔ Debug fast  
✔ Trace functions automatically  
✔ Measure execution time  
✔ Remove debug lines automatically  
✔ Work everywhere  
✔ Zero dependencies  

---

## Features

- Works in Python 3+  
- No external dependencies  
- Uses `print` or `pprint` automatically for complex objects  
- Shows file and line number  
- Optional execution timer (`timeit=True`)  
- Trace decorator to log function calls and returns (`@siren.trace`)  
- Can remove all debug calls automatically  
- Safe cleaner using Python tokenize  
- Works in Django / Flask / FastAPI / scripts / CLI  
- Colored output with emoji  

---

## Installation

Install Siren via pip:

```bash
pip install siren-debug

Then, add siren to your framework’s configuration:

# Django example
INSTALLED_APPS = [
    # ...
    "siren",
]

Usage
x = 10
data = {"a": 1, "b": [1, 2, 3]}

siren(x)
siren(data)

Output:

[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN core.py:11] data = {'a': 1, 'b': [1, 2, 3]}

Siren automatically uses pprint for complex objects.

Multiple values
siren(x, data, user)
Timer
siren(x, timeit=True)

Outputs the value and the elapsed time:

[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN TIME] 0.000123s
Trace decorator
@siren.trace
def add(a, b):
    return a + b

add(2, 3)

Output:

[🧜‍ SIREN core.py:10] Calling add
[🧜‍ SIREN core.py:11] Returned from add -> 5
Cleaner (remove all siren calls)

This is the main feature.

Remove all lines that call siren(...):

siren-clean

Example:

Before:

siren(x)
print("hello")
siren(data)

After:

print("hello")

Cleaner is safe and uses Python tokenize.
It will not remove comments or strings.

Why Siren?

Using print or pprint for debugging is easy,
but removing them later is painful.

Siren solves this.

Use:

siren(value)

And later:

clean all

Done.

Goals

Minimal

Safe

Cross-version

No dependencies

Easy cleanup

Works offline

Function tracing & timing

License

MIT