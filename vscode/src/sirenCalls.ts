// Pure text helpers, kept free of the vscode API so they can be unit-tested
// with plain Node.

const CALL_RE = /(?<![\w.])siren(?:\.\w+)?\s*\(/;
const DECORATOR_RE = /^\s*@siren\.\w+/;
const DEF_RE = /^\s*def\s+siren\b/;
const IMPORT_RE = /^\s*from\s+siren\s+import\s+siren\b/m;

/** 0-based line numbers that contain a siren call or @siren.* decorator. */
export function findSirenLines(text: string): number[] {
  const result: number[] = [];
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^\s*#/.test(line) || DEF_RE.test(line)) {
      continue;
    }
    const code = stripTrailingComment(line);
    if (CALL_RE.test(code) || DECORATOR_RE.test(code)) {
      result.push(i);
    }
  }
  return result;
}

function stripTrailingComment(line: string): string {
  let quote: string | null = null;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quote) {
      if (ch === "\\") {
        i++;
      } else if (ch === quote) {
        quote = null;
      }
    } else if (ch === "'" || ch === '"') {
      quote = ch;
    } else if (ch === "#") {
      return line.slice(0, i);
    }
  }
  return line;
}

export function hasSirenImport(text: string): boolean {
  return IMPORT_RE.test(text);
}

/**
 * 0-based line where `from siren import siren` should go: after a shebang,
 * encoding comments, the module docstring, and `from __future__` imports,
 * which Python requires to come first.
 */
export function importInsertLine(text: string): number {
  const lines = text.split(/\r?\n/);
  let i = 0;
  while (i < lines.length && /^\s*#/.test(lines[i])) {
    i++;
  }
  const docMatch = i < lines.length ? /^\s*[rRuUbB]*("""|''')/.exec(lines[i]) : null;
  if (docMatch) {
    const quote = docMatch[1];
    const rest = lines[i].slice(lines[i].indexOf(quote) + 3);
    if (rest.includes(quote)) {
      i++;
    } else {
      i++;
      while (i < lines.length && !lines[i].includes(quote)) {
        i++;
      }
      i++;
    }
  }
  let afterFuture = -1;
  for (let j = i; j < lines.length; j++) {
    if (/^from\s+__future__\s+import\b/.test(lines[j])) {
      afterFuture = j + 1;
    } else if (lines[j].trim() !== "" && !/^\s*#/.test(lines[j])) {
      break;
    }
  }
  return Math.min(afterFuture >= 0 ? afterFuture : i, lines.length);
}

/** Indentation for a new `siren(...)` line placed after `line`. */
export function indentAfter(line: string, indentUnit: string): string {
  const indent = /^\s*/.exec(line)![0];
  return stripTrailingComment(line).trimEnd().endsWith(":") ? indent + indentUnit : indent;
}

/** One-line, length-limited rendering of a value for end-of-line display. */
export function summarize(value: string, max = 80): string {
  const flat = value.replace(/\s+/g, " ").trim();
  return flat.length > max ? flat.slice(0, max - 1) + "…" : flat;
}

export interface CleanPreview {
  files: { path: string; lines: number }[];
  total: number;
}

/** Number of lines `siren-clean` reports it removed. */
export function parseRemovedCount(output: string): number {
  const m = /(\d+) linhas removidas/.exec(output.replace(/\x1b\[[0-9;]*m/g, ""));
  return m ? Number(m[1]) : 0;
}

/** Files `siren-clean` reported and skipped ("! path (Error: message)"). */
export function parseSkipped(output: string): string[] {
  return output
    .split(/\r?\n/)
    .filter((line) => line.startsWith("! "))
    .map((line) => line.slice(2).trim());
}

/** Parse `siren-clean --dry-run` output. */
export function parseCleanPreview(output: string): CleanPreview {
  const files: { path: string; lines: number }[] = [];
  for (const line of output.split(/\r?\n/)) {
    const m = /^✓ (.+) \((\d+) linhas\)\s*$/.exec(line);
    if (m) {
      files.push({ path: m[1], lines: Number(m[2]) });
    }
  }
  return { files, total: files.reduce((sum, f) => sum + f.lines, 0) };
}
