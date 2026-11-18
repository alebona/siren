# Siren for VS Code

Print-debugging for Python, without the cleanup. Write `siren(x)`, run your code, and see the value at the end of that line in the editor. When you're done, remove every call in one click.

Nothing to `pip install`: the extension carries its own runtime and makes `siren` available to any Python program you start from a VS Code terminal or the Python debugger.

## Debug

**Values inline.** Each `siren(...)` call shows its latest value at the end of its line. Hover to see the last five values (handy in loops). Every value is also logged to the **Siren** output channel (`Siren: Show Captured Values`).

```python
user = load_user(42)
siren(user)          🧜 user = {'id': 42, 'name': 'Alex', 'plan': 'pro'}
for i in range(3):
    siren(i, label="loop")   🧜 i = 2 (last of 3)
```

**Insert a call.** Press `Ctrl+Alt+S` (`Cmd+Alt+S` on macOS): Siren adds `siren()` with the cursor between the parentheses, ready to type (on a blank line, right there; otherwise on a new line below). With the cursor on a variable, its name comes pre-filled and selected. With an expression selected, it wraps it in `siren(...)`. It also adds `from siren import siren` if the file doesn't have it.

**Highlighted calls.** Lines with `siren(...)` or `@siren.*` decorators are tinted and marked in the scrollbar, and the status bar shows how many the current file has, so none slip into a commit.

**Remove them all.** `Siren: Remove siren() Calls from This File` (or click the status bar count) and `Siren: Remove siren() Calls from Workspace` delete the calls and their imports. The workspace command first lists the files that will change. When a call is the only line in a block, such as a loop whose body is just `siren(i)`, Siren leaves a `pass` in its place so the code stays valid.

The rest of the API works too: `@siren.trace` logs a function's calls and return values, `siren.diff(a, b)` shows what changed between two objects, `siren.memory()` prints memory use, `with siren.catch():` prints a readable traceback, and `siren.breakpoint()` pauses and lists local variables.

## Code quality

Python files are checked when you open or save them, and the results land in the **Problems** panel: unused imports and functions, bare `except:`, `pdb.set_trace()` or `breakpoint()` left in the code, TODO and FIXME comments, and functions whose cyclomatic complexity is above 10 (configurable). `Siren: Check Code Quality in Workspace` checks every file at once.

## .env drift

When a workspace folder has both `.env` and `.env.example`, Siren marks keys documented in `.env.example` but missing from `.env`, and keys set in `.env` that `.env.example` doesn't mention. A quick fix (`Ctrl+.`) adds the missing key to the other file.

## Templates

Right-click a folder in the Explorer and pick **New from Template...** to create a script with a `main()`, a class, a data class, a unittest file, or a package with `__init__.py`, `core.py` and tests.

## Snippets

The Siren sidebar keeps the code you reuse. Click a snippet to insert it at the cursor. **+** opens a form with the name, tags and code together (pre-filled with your selection, if any); the pencil opens the same form to edit one. Write `{{name}}` where a value changes: it becomes a field you fill in and move through with Tab. Snippets can be filtered, copied, and exported or imported as JSON.

## HTTP requests

Send a request from the sidebar (**New Request**: method, URL, optional JSON body) and the response opens beside your code, with status and headers on top and JSON pretty-printed. Save the ones you repeat. A saved request is a JSON file you can edit, with a **Send request** link at the top.

## How the runtime gets in

The extension adds its bundled `siren` package to `PYTHONPATH` for:

- integrated terminals opened after the extension starts (including **Run Python File**), and
- Python debug sessions (`debugpy`).

A `sitecustomize` module then registers `siren` as a builtin, so calls work even without the import. Any `sitecustomize` your environment already has still runs.

Programs started outside VS Code don't get the runtime, so remove the calls before you ship. Terminals that were already open when the extension started don't get it either; open a new one.

## Settings

| Setting | Default | |
| --- | --- | --- |
| `siren.injectRuntime` | `true` | Put the runtime on `PYTHONPATH` for terminals and debug sessions. |
| `siren.inlineValues` | `true` | Show values at the end of the line. |
| `siren.highlightCalls` | `true` | Highlight calls and show the status bar count. |
| `siren.addImport` | `true` | Add `from siren import siren` when inserting a call. |
| `siren.quality.enabled` | `true` | Check Python files on open and save. |
| `siren.quality.complexityThreshold` | `10` | Flag functions above this cyclomatic complexity. |
| `siren.envCheck.enabled` | `true` | Compare `.env` with `.env.example`. |
| `siren.pythonPath` | `""` | Interpreter for Siren's checks and tools. Empty uses the Python extension's selected interpreter, then `python`. |

## Requirements

Python 2.7 or 3.6+ on your machine. The [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) is optional; when it's installed, Siren uses the interpreter you selected there.
