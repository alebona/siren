# Changelog

All notable changes to the `siren-debug` project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
