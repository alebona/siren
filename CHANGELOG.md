# Changelog

All notable changes to the `siren-debug` project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

Accumulating here rather than publishing a version per change - see
`ROADMAP.md` for the pro-tier context.

### Added
- `siren-snippet copy <name>` — copies a snippet straight to the system clipboard (`pbcopy`/`clip`/`xclip`/`xsel`, no external dependency).
- `siren-snippet edit <name>` — opens a snippet in `$EDITOR`/`$VISUAL`.
- `siren-snippet rename <old> <new>` — renames a snippet, preserving its tags/timestamps.
- `siren-snippet save --tag ...`, `siren-snippet list --tag ...`, and `siren-snippet tags` (every tag in use, with counts).
- `siren-snippet search <term>` — matches by name, tag, or content.
- `{{placeholder}}` markers in a snippet's content, filled in via `--var key=value` on `show`/`copy`.
- `siren-snippet export`/`import` — round-trips all snippets (content, tags, timestamps) through a JSON file, for backup or moving to another machine.
- `siren-snippet save --file <path>` — reads content from a file instead of stdin, defaulting the snippet name to the file's basename.
- `siren-snippet list` now shows tags, last-updated time, and a one-line content preview instead of just the bare name.
- `siren-login` (`signup`, `use-key`, `status`, `logout`) and `siren-events` (`list`, `show`) — the first pro-tier feature: exception capture. `siren.report()` sends a caught exception to your `siren-pro` workspace; never raises on its own even if you're not logged in or the backend is unreachable.

### Changed
- `siren-snippet save` now refuses to overwrite an existing snippet unless you pass `--force`, instead of silently clobbering it (matches `siren-scaffold`'s existing behavior).

### Fixed
- `http_client.send()` didn't close the underlying connection on either the success or error path, surfacing as `ResourceWarning: unclosed socket` once something (the new `siren-login`) actually hit non-2xx responses through it.

---

## [0.6.3] - 2026-09-15

### Fixed
- `siren-scaffold class`/`dataclass`/`test` mangled an already-cased class name: `IssoEhUmaClasse` became `Issoehumaclasse`, because `_class_name()` used `str.capitalize()`, which also lowercases everything after the first letter. Now only the first letter of each `-`/`_`-separated part is capitalized, preserving any camelCase/PascalCase already present in the name you typed.

---

## [0.6.2] - 2026-09-15

### Fixed
- `siren-quality` (`deadcode`, `lint`, `complexity`) never actually parsed any file on Python 2.7: `ast.parse()`/`compile()` on Python 2 raises `SyntaxError: encoding declaration in Unicode string` when given an already-decoded unicode string that still contains a `# -*- coding: utf-8 -*-` line, which every file in this project (and most real Python 2 codebases) has. Every file silently failed to parse, and `deadcode`/`lint` then printed "no issues found" as if analysis had actually happened - a false-clean report. `complexity` had the same parse failure but no misleading message, so it just went silent. Source is now re-encoded to bytes before parsing, letting the parser detect the encoding itself (Python 3 behavior is unchanged - it already accepted this fine). All three commands also now report any file that still fails to parse and exit non-zero instead of staying quiet about it.

---

## [0.6.1] - 2026-09-14

### Fixed
- `siren-autoload on` crashed on Python 2.7 with `TypeError: write() argument 1 must be unicode, not str`. The same class of bug (writing a plain `str` through `io.open(..., encoding="utf-8")`, which requires `unicode` on Python 2) also affected `siren-scaffold` (all templates) and the credential/collection files written by the in-progress pro-tier CLI (`siren-login`, `siren-http --save`). All four now decode to `unicode` first, matching the pattern already used safely in `core.py` and `siren-snippet`.

---

## [0.6.0] - 2026-09-13

### Added

Completes the free-tier feature set from the project roadmap (see `ROADMAP.md`), turning siren from a debug-only helper into a broader local dev toolbelt. Every new tool ships with zero external dependencies and works on Python 2.7 and 3.6+.

- `siren.memory(label=None, top=0)` — print current/peak traced memory usage (`tracemalloc`); prints a clear "not supported" message on Python 2, where `tracemalloc` doesn't exist.
- `siren.catch(label=None)` — context manager that prints a colored, siren-formatted traceback on exception and re-raises it (never swallows errors).
- `siren-scaffold` — generate small file/project skeletons: `script`, `package`, `class`, `dataclass` (plain-Python, no `dataclasses` module needed), `test`.
- `siren-env diff` — compare `.env` against `.env.example` and report missing/extra keys; non-zero exit code on drift, so it can gate CI.
- `siren-snippet` — save/show/list/remove small text snippets from the terminal (`~/.siren/snippets/`).
- `siren-http` — a small httpie-like HTTP client (GET/POST/PUT/PATCH/DELETE, custom headers, JSON/raw body) built on `urllib` only, plus local, replayable request collections (`--save`, `replay`, `list`).
- `siren-quality` — local code-quality helpers built on `ast`: `deadcode` (unused imports/module-level defs), `lint` (bare `except:`, leftover `pdb.set_trace()`/`breakpoint()`, TODO/FIXME comments), `complexity` (cyclomatic complexity per function).
- `siren.patch_requests()` / `siren.patch_httpx()` — opt-in logging of every HTTP call made through `requests` or `httpx` (method/url/status/duration), with matching `unpatch_*()` calls. Neither library is a dependency; they're only imported when a patch function is actually called.

---

## [0.5.0] - 2026-09-13

### Added
- Python 2.7 support alongside Python 3.6+ for the core features (`siren()`, `trace`, `diff`, `breakpoint`, `siren-clean`, `siren-autoload`). Package now ships as a universal wheel (`py2.py3-none-any`).
- `siren-clean` now accepts a broader set of ignored directories (`.venv`, `doc`, `docs`, `.git`, `node_modules`, in addition to `venv`/`__pycache__`).

### Fixed
- `siren.set_logfile(...)` no longer silently fails to write on Python 2, and no longer corrupts non-ASCII output when it does write.
- `siren-clean` no longer silently reads/writes source files as raw bytes on Python 2, which could corrupt files containing non-ASCII characters (e.g. accented comments).

---

## [0.4.0] - 2026-07-15

### Added
- `siren-autoload` command (`on` / `off` / `status`) to inject `siren` into Python builtins for every process in the current environment via a `.pth` file in `site-packages`, so it can be used anywhere without `from siren import siren` in each file. Opt-in per environment.

### Fixed
- `siren-clean` no longer strips `def siren(...)` (or any function definition) when it happens to be named `siren` — previously this deleted the `def` line itself and left an indented, syntactically invalid body.
- `siren-clean` no longer removes `from siren import siren`-looking text found inside multi-line string literals (e.g. test fixtures).
- `siren-clean` now verifies the cleaned output still compiles before writing; if removing a call would leave an empty code block, the file is left untouched instead of being corrupted.
- Fixed `UnicodeEncodeError` crashing every `siren(...)` call, `siren-clean`, and `siren-autoload` output on consoles using a narrow encoding (e.g. the cp1252 default on plain Windows terminals) — output now falls back gracefully instead of crashing.

---

## [0.3.0] - 2026-06-08

### Added
- **Conditional logging**:
  - `siren(x, if_equals=value)` — Only log when value matches
  - `siren(x, if_len_gt=N)` — Only log if length > N
  - `siren(x, if_len_lt=N)` — Only log if length < N
  - `siren(x, if_true=...)` — Only log if truthy
  - `siren(x, if_false=...)` — Only log if falsy
- **Object diff**: `siren.diff(before, after)` to compare dicts, lists, and objects
- **Interactive breakpoint**: `siren.breakpoint()` to pause and inspect variables
- GitHub Actions workflows for automated testing and PyPI publishing

### Added
- Quiet mode: `siren(x, quiet=True)` to suppress output for specific calls
- Global quiet mode: `siren.set_quiet(True)` to disable all siren output
- Logging to file: `siren.set_logfile("debug.log")` to save debug output
- Global configuration: `siren.get_config()` to inspect current settings
- Improved trace decorator with:
  - Smart truncation for large objects (max 80-100 chars)
  - Return type display: `[int]`, `[dict]`, `[list]`, etc.
  - Exception capture and logging with type and message
  - Configurable options: `timeit`, `show_args`, `show_return`, `show_type`
  - Better performance using `time.perf_counter()`

### Changed
- Output format now displays full relative path from project root
- Trace decorator now formats arguments inline for better readability
- Siren output respects quiet mode and logfile configuration globally

### Fixed
- Trace decorator now properly handles None return values
- Exception handling in trace decorator no longer suppresses the original exception

---

## [0.2.0] - 2026-06-07

### Added
- Trace decorator `@siren.trace` for function call and return logging
- Timer support with `timeit=True` parameter
- Support for multiple values: `siren(x, y, z)`
- Label support: `siren(value, label="CONTEXT")`
- Automatic `pprint` formatting for complex objects
- Colored output with emoji and timestamp
- Safe cleaner using Python tokenize

### Changed
- Complete rewrite of trace logic for better readability
- Improved argument extraction from source code

---

## [0.1.3] - Initial PyPI Release

### Added
- Basic `siren()` debug function
- `siren-clean` command to remove debug calls
- Support for Python 3.6+
- No external dependencies
- Colored output support
- File and line number display
