<p align="center">
  <img src="vscode/media/icon.png" width="128" alt="Siren icon: a crystal mermaid tail rising from the water">
</p>

<h1 align="center">Siren</h1>

<p align="center">
  Print-debugging for Python, without the cleanup.<br>
  A VS Code extension: write <code>siren(x)</code>, run your code, see the value at the end of the line. Remove every call in one click.
</p>

<p align="center">
  <a href="https://marketplace.visualstudio.com/items?itemName=alebona.siren"><img src="https://vsmarketplacebadges.dev/version-short/alebona.siren.svg" alt="VS Code Marketplace version"></a>
  <a href="https://marketplace.visualstudio.com/items?itemName=alebona.siren"><img src="https://vsmarketplacebadges.dev/installs-short/alebona.siren.svg" alt="Installs"></a>
  <img src="https://img.shields.io/badge/Python-2.7%20%7C%203.6%2B-3776AB" alt="Python 2.7 and 3.6+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
</p>

<p align="center"><b>English</b> · <a href="README.pt.md">Português</a></p>

---

## Install

Search for **Siren** in the VS Code Extensions panel (`Ctrl+Shift+X`), or install it from the [Marketplace page](https://marketplace.visualstudio.com/items?itemName=alebona.siren), or from a terminal:

```bash
code --install-extension alebona.siren
```

There is nothing to `pip install`. The extension carries its own Python runtime and makes `siren` available to every Python program you start from VS Code. You only need Python 2.7 or 3.6+ on your machine.

## Quick start

```python
user = {"name": "Ana", "items": [1, 2, 3]}
siren(user)

for i in range(3):
    siren(i, label="loop")
```

Press ▶ **Run current file** at the top of the editor (or run the file in a VS Code terminal, or with F5). Each value shows at the end of its line:

```text
siren(user)                 🧜 user = {'name': 'Ana', 'items': [1, 2, 3]}
    siren(i, label="loop")  🧜 i = 2 (last of 3)
```

No import needed: under VS Code, `siren` is a builtin. When you're done, click the **🧜** counter in the status bar to remove every call from the file.

## What's in the extension

Everything sits in the Siren sidebar (the mermaid tail icon), and in the command palette under **Siren:**.

| | |
| --- | --- |
| **Inline values** | Each `siren()` shows its latest value at the end of its line; hover for the last five. |
| **Insert** | `Ctrl+Alt+S` adds `siren()` with the cursor inside, ready to type, or wraps the selection in `siren(...)`. |
| **Run current file** | Runs the file in a new terminal with Siren loaded, so values show up with no setup. |
| **Calls** | Every `siren()` in the workspace, grouped by file, with its last value. The sidebar icon shows the total. |
| **Clean up** | Remove the calls from one file or the whole workspace, with a preview. A call that is a block's only line becomes `pass`. |
| **Code quality** | Unused imports and functions, bare `except:`, leftover breakpoints, TODOs and complex functions, in the Problems panel. |
| **.env drift** | Keys missing from `.env` or `.env.example`, with a quick fix that adds them. |
| **Templates** | New script, class, data class, test or package from the Explorer's right-click menu. |
| **Snippets** | Save code you reuse in a form (name, tags, code) and insert it with one click; `{{name}}` becomes a field to fill in. |
| **HTTP requests** | Send requests, save the ones you repeat, and read the response beside your code. |

The [extension's own README](vscode/README.md) covers each feature and its settings.

## The `siren()` API

`siren()` returns what you pass it, so it can go inside an expression:

```python
siren(x, data, user)              # several values at once
total = siren(compute())          # still returns compute()'s value
siren(order, label="BEFORE SAVE") # tag a call
siren(x, timeit=True)             # also print how long the call took
siren(items, if_len_gt=100)       # only when len(items) > 100
siren(x, if_equals=5)             # also: if_len_lt, if_true, if_false
siren(x, quiet=True)              # keep the call, print nothing
```

More tools on the same object:

```python
@siren.trace                      # log each call: arguments, return value, time, exceptions
def add(a, b):
    return a + b

siren.diff(before, after)         # what changed between two dicts, lists or objects
siren.breakpoint()                # pause and print the local variables
siren.memory(top=5)               # current and peak memory, plus the top allocation sites (Python 3.4+)

with siren.catch():               # print a readable traceback, then re-raise
    risky_call()

siren.patch_requests()            # log every call made through requests (also: patch_httpx)
siren.set_quiet(True)             # silence every call until set_quiet(False)
siren.set_logfile("debug.log")    # also write the output to a file
```

`@siren.trace` takes `timeit`, `show_args`, `show_return` and `show_type`, all `True` by default.

## How the runtime gets in

The extension puts its bundled `siren` package on `PYTHONPATH` for integrated terminals opened after it starts (including **Run Python File**) and for Python debug sessions. A `sitecustomize` module then registers `siren` as a builtin; any `sitecustomize` your environment already has still runs.

Programs started anywhere else don't get the runtime: an external terminal, a terminal opened before the extension loaded, a server you start outside VS Code, or a script that an AI coding assistant runs for you. There, a leftover `siren(x)` raises `NameError`, so remove the calls before you ship.

## Python versions

The runtime supports Python 2.7 and 3.6+. CI runs the test suite on Python 3.10 to 3.13 (Linux, Windows and macOS), and an end-to-end check of a legacy-style project (Python 2 syntax, accented text, `coding:` line) on Python 2.7 and 3.

## Siren Pro

Pro will bring production into the editor: exceptions from your servers shown on the line that raised them, and each function's real response times above its definition, plus alerts, sync between machines and team workspaces. It is in development; the free extension stays free.

## Repository

| Path | What it is |
| --- | --- |
| `vscode/` | The VS Code extension (TypeScript) |
| `siren/` | The Python runtime the extension bundles: `siren()`, cleanup, quality checks, snippets, HTTP |
| `siren/_bridge.py` | JSON-over-stdin entry point the extension uses to call the Python side |
| `tests/` | Python tests, plus `smoke_legacy.py`, the end-to-end check that also runs on Python 2.7 |

### Development

```bash
# Python tests
python -m unittest discover -s tests
python tests/smoke_legacy.py

# Extension: unit tests, then the integration suite in a real VS Code
cd vscode
npm ci
npm test
npm run test:integration
```

Press F5 in VS Code with the `vscode/` folder open to try the extension in a development window.

### Releases

Bump `version` in `vscode/package.json` and add a `vscode/CHANGELOG.md` entry, merge to `main`, then push a `vscode-v<version>` tag on `main`. The [publish workflow](.github/workflows/publish-vscode.yml) runs every test and publishes to the Marketplace.

### The `siren-debug` PyPI package

Siren started as the `siren-debug` package on PyPI, with `siren-*` terminal commands. That package is being retired in favor of the extension, which includes everything it did. Its last release stays installable for anyone who still depends on it.

## License

[MIT](LICENSE)
