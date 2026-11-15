import * as assert from "node:assert/strict";
import { test } from "node:test";
import { appendKeyText, envDrift, exampleFromEnv, parseEnvKeys } from "../envFile";

test("exampleFromEnv keeps keys and comments but drops every value", () => {
  assert.equal(
    exampleFromEnv("# database\nDB_URL=postgres://user:secret@host/db\n\nexport API_KEY = abc123\nDEBUG=\r\n"),
    "# database\nDB_URL=\n\nexport API_KEY =\nDEBUG=\r\n",
  );
});

test("parseEnvKeys skips comments and blanks, keeps first line, strips export", () => {
  const keys = parseEnvKeys("# db\n\nDB_URL=postgres://x\nexport API_KEY = abc\nnot a pair\nDB_URL=again\r\n");
  assert.deepEqual([...keys], [
    ["DB_URL", 2],
    ["API_KEY", 3],
  ]);
});

test("envDrift reports both directions with lines in the right file", () => {
  const drift = envDrift("A=\nB=\nC=\n", "A=1\nD=2\n");
  assert.deepEqual(drift.missingInEnv, [
    { key: "B", line: 1 },
    { key: "C", line: 2 },
  ]);
  assert.deepEqual(drift.missingInExample, [{ key: "D", line: 1 }]);
});

test("appendKeyText adds a newline only when needed", () => {
  assert.equal(appendKeyText("", "X"), "X=\n");
  assert.equal(appendKeyText("A=1\n", "X"), "X=\n");
  assert.equal(appendKeyText("A=1", "X"), "\nX=\n");
});
