# Changelog

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
