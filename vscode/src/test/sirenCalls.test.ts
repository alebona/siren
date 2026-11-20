import * as assert from "node:assert/strict";
import { test } from "node:test";
import {
  findSirenLines,
  hasSirenImport,
  importInsertLine,
  indentAfter,
  parseCleanPreview,
  parseRemovedCount,
  parseSkipped,
  summarize,
} from "../sirenCalls";

test("findSirenLines finds calls and decorators, skips comments and defs", () => {
  const src = [
    "from siren import siren", // 0: import, not a call
    "siren(x)", // 1
    "    y = siren(compute())", // 2
    "# siren(x)", // 3
    "@siren.trace", // 4
    "def siren(x):", // 5
    "x = 1  # siren(x)", // 6
    "mysiren(x)", // 7
    "obj.siren(x)", // 8
    "siren.diff(a, b)", // 9
    "print('#', siren(z))", // 10: # inside a string isn't a comment
  ].join("\n");
  assert.deepEqual(findSirenLines(src), [1, 2, 4, 9, 10]);
});

test("findSirenLines handles CRLF", () => {
  assert.deepEqual(findSirenLines("a = 1\r\nsiren(a)\r\n"), [1]);
});

test("hasSirenImport", () => {
  assert.equal(hasSirenImport("import os\nfrom siren import siren\n"), true);
  assert.equal(hasSirenImport("import os\n"), false);
});

test("importInsertLine goes after shebang, docstring and __future__", () => {
  assert.equal(importInsertLine("x = 1\n"), 0);
  assert.equal(importInsertLine("#!/usr/bin/env python\n# -*- coding: utf-8 -*-\nx = 1\n"), 2);
  assert.equal(importInsertLine('"""Doc."""\nx = 1\n'), 1);
  assert.equal(importInsertLine('"""\nLong\ndoc.\n"""\nimport os\n'), 4);
  assert.equal(importInsertLine('"""Doc."""\nfrom __future__ import annotations\n\nimport os\n'), 2);
});

test("indentAfter indents one level after a block opener", () => {
  assert.equal(indentAfter("    x = 1", "    "), "    ");
  assert.equal(indentAfter("    for x in y:", "    "), "        ");
  assert.equal(indentAfter("if a:  # comment", "    "), "    ");
});

test("summarize flattens and truncates", () => {
  assert.equal(summarize("{'a': 1,\n 'b': 2}"), "{'a': 1, 'b': 2}");
  assert.equal(summarize("x".repeat(100), 10), "xxxxxxxxx…");
});

test("parseSkipped lists the files siren-clean skipped", () => {
  assert.deepEqual(parseSkipped("! app/a.py (ValueError: boom)\r\n[SIREN CLEAN] 2 linhas removidas\n! b.py (IOError: x)\n"), [
    "app/a.py (ValueError: boom)",
    "b.py (IOError: x)",
  ]);
  assert.deepEqual(parseSkipped("nothing\n"), []);
});

test("parseRemovedCount reads the colored siren-clean summary", () => {
  assert.equal(parseRemovedCount("\x1b[38;2;255;105;180m[SIREN CLEAN] \x1b[38;2;255;105;180m3 linhas removidas\x1b[0m\n"), 3);
  assert.equal(parseRemovedCount("garbage"), 0);
});

test("parseCleanPreview reads siren-clean --dry-run output", () => {
  const out = "✓ app\\views.py (3 linhas)\n✓ app/models.py (1 linhas)\n[SIREN CLEAN] 4 linhas encontradas\n";
  assert.deepEqual(parseCleanPreview(out), {
    files: [
      { path: "app\\views.py", lines: 3 },
      { path: "app/models.py", lines: 1 },
    ],
    total: 4,
  });
});
