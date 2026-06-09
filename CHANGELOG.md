# Changelog

All notable changes to the `siren-debug` project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
