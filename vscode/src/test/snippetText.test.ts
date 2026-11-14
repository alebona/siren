import * as assert from "node:assert/strict";
import { test } from "node:test";
import { parseTags, toSnippetSyntax, validateName } from "../snippetText";

test("placeholders become tab stops; repeats share one", () => {
  assert.equal(
    toSnippetSyntax("SELECT * FROM {{table}} WHERE id = {{id}} -- {{table}}"),
    "SELECT * FROM ${1:table} WHERE id = ${2:id} -- ${1:table}",
  );
});

test("literal $, } and backslash are escaped", () => {
  assert.equal(toSnippetSyntax("echo $HOME } \\n"), "echo \\$HOME \\} \\\\n");
  assert.equal(toSnippetSyntax("f'{x}'"), "f'{x\\}'");
});

test("content without placeholders is only escaped", () => {
  assert.equal(toSnippetSyntax("print('hi')\n"), "print('hi')\n");
});

test("validateName rejects path characters and empties", () => {
  assert.equal(validateName("my-snippet"), undefined);
  assert.ok(validateName(""));
  assert.ok(validateName("a/b"));
  assert.ok(validateName("..x"));
});

test("parseTags trims, drops empties and leading #", () => {
  assert.deepEqual(parseTags(" sql, #db ,, x"), ["sql", "db", "x"]);
});
