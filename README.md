# Siren

Minimalist debug tool for Python.

Siren is a lightweight alternative to print / pprint, designed to work
with any Python version, including Python 2.7, and any framework like Django,
Flask, FastAPI, or pure Python.

The main goal of Siren is simple:

✔ Debug fast  
✔ Remove debug lines automatically  
✔ Work everywhere  
✔ Zero dependencies  

---

## Features

- Works in Python 2.7+
- Works in Python 3+
- No external dependencies
- Uses print or pprint automatically
- Shows file and line number
- Can remove all debug calls automatically
- Safe cleaner using tokenize
- Works in Django / Flask / scripts / CLI

---

## Installation (local)

Clone the repository:


git clone https://github.com/youruser/siren.git


Copy the `siren` folder into your project
or add it to PYTHONPATH.

Example:


from siren import siren


---

## Usage


from siren import siren

x = 10
data = {"a": 1, "b": [1, 2, 3]}

siren(x)
siren(data)


Output:


[SIREN file.py:10] 10
[SIREN file.py:11] {'a': 1, 'b': [1, 2, 3]}


Siren automatically uses pprint for complex objects.

---

## Multiple values


siren(x, data, user)


---

## Cleaner (remove all siren calls)

This is the main feature.

Remove all lines that call `siren(...)`:


python -m siren.clean .


or


python siren/clean.py .


Example:

Before:


siren(x)
print("hello")
siren(data)


After:


print("hello")


Cleaner is safe and uses Python tokenize.

It will NOT remove comments or strings.

---

## Why Siren?

Using print or pprint for debugging is easy,
but removing them later is painful.

Siren solves this.

Use:


siren(value)


And later:


clean all


Done.

---

## Goals

- Minimal
- Safe
- Cross-version
- No dependencies
- Easy cleanup
- Works offline

---

## License

MIT