# Changelog

## 1.2.0

- New **Calls** section in the Siren sidebar: every `siren()` call in the workspace, grouped by file, with its line and last captured value. Click one to jump to it. It updates as you edit (unsaved changes included), create and delete files, and skips `.venv`, `node_modules` and other installed code.
- The Siren icon in the activity bar shows how many calls the workspace has.
- **Run current file** (▶ at the top of Python editors, the Actions panel, or `Siren: Run Python File with Siren`): runs the file in a new terminal with Siren loaded, so its values show up with no setup.
- **Show captured values** explains why the list is empty when nothing has been captured yet, and offers to run the current file.
- The status bar shows this file's count and the workspace's (`🧜 2 · 7`). With none in the current file, it shows the workspace total and opens the Calls list.

## 1.1.0

- New **Actions** section at the top of the Siren sidebar: insert `siren()`, show or clear captured values, remove calls from the file or workspace, check code quality, check `.env`, and create a file from a template, each one click away.
- New command: `Siren: Check .env Against .env.example`.

## 1.0.3

- Removing `siren()` calls no longer skips a file when a call is the only line in a block (for example `for i in x: siren(i)`). Siren leaves a `pass` there and removes everything else; before, the whole file was left untouched.
- Removing calls keeps the file's own line endings. Before, a file with LF endings came back with CRLF on Windows (and the reverse elsewhere), so git showed every line as changed.
- Code quality no longer flags test classes and functions, decorated functions (`@app.get`, `@pytest.fixture`, ...) or `from __future__` imports as unused.

## 1.0.2

- New icon: a glowing mermaid tail rising from the water.

## 1.0.1

- Siren now has its own icon in the Marketplace and the Extensions panel.

## 1.0.0

First release of Siren as a VS Code extension. Everything the `siren-debug` Python package did now works inside the editor, with nothing to `pip install`.

- `siren(x)` values shown at the end of their line, with the last five on hover and a log in the Siren output channel.
- `Ctrl+Alt+S` wraps the selection in `siren(...)` or logs the variable under the cursor.
- Lines with `siren(...)` are highlighted, and the status bar counts them.
- Remove every `siren(...)` call from a file or the whole workspace, with a preview.
- Code quality checks in the Problems panel: unused imports and functions, bare `except:`, leftover breakpoints, TODOs, and high complexity.
- `.env` and `.env.example` compared as you edit, with a quick fix that adds a missing key.
- New file or package from a template, from the Explorer's right-click menu.
- Snippets sidebar: insert at the cursor with `{{name}}` fields as tab stops, copy, edit, tag, import and export.
- HTTP requests sidebar: send, save and edit requests, with the response opened beside the editor.
