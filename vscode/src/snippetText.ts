// Turns a saved siren snippet into VS Code snippet syntax: each {{name}}
// placeholder becomes a tab stop (the same name repeated = one mirrored stop)
// and everything else is escaped so it's inserted literally.

const VAR_RE = /\{\{(\w+)\}\}/g;

function escapeLiteral(text: string): string {
  return text.replace(/[\\$}]/g, (ch) => "\\" + ch);
}

export function toSnippetSyntax(content: string): string {
  const stops = new Map<string, number>();
  let out = "";
  let last = 0;
  for (const match of content.matchAll(VAR_RE)) {
    out += escapeLiteral(content.slice(last, match.index));
    const name = match[1];
    if (!stops.has(name)) {
      stops.set(name, stops.size + 1);
    }
    out += `\${${stops.get(name)}:${name}}`;
    last = match.index! + match[0].length;
  }
  return out + escapeLiteral(content.slice(last));
}

/** Valid snippet/request name: becomes a file name, so no path separators. */
export function validateName(name: string): string | undefined {
  if (!name.trim()) {
    return "Enter a name.";
  }
  if (/[\\/:*?"<>|]/.test(name) || name.startsWith(".")) {
    return 'Names can\'t contain \\ / : * ? " < > | or start with a dot.';
  }
  return undefined;
}

/** "sql, db  ,x" -> ["sql", "db", "x"] */
export function parseTags(input: string): string[] {
  return input
    .split(",")
    .map((t) => t.trim().replace(/^#/, ""))
    .filter(Boolean);
}
