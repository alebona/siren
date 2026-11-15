// Pure .env helpers (no vscode API), mirroring siren/envtool.py's parsing:
// blank lines and comments are skipped, the key is what comes before "=".

/** Key -> 0-based line of its first definition. */
export function parseEnvKeys(text: string): Map<string, number> {
  const keys = new Map<string, number>();
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line || line.startsWith("#") || !line.includes("=")) {
      continue;
    }
    const key = line.split("=", 1)[0].trim().replace(/^export\s+/, "");
    if (key && !keys.has(key)) {
      keys.set(key, i);
    }
  }
  return keys;
}

export interface EnvKey {
  key: string;
  line: number;
}

export interface EnvDrift {
  /** Declared in .env.example but missing from .env (line in .env.example). */
  missingInEnv: EnvKey[];
  /** Set in .env but not documented in .env.example (line in .env). */
  missingInExample: EnvKey[];
}

export function envDrift(exampleText: string, envText: string): EnvDrift {
  const example = parseEnvKeys(exampleText);
  const env = parseEnvKeys(envText);
  const missing = (from: Map<string, number>, other: Map<string, number>) =>
    [...from].filter(([key]) => !other.has(key)).map(([key, line]) => ({ key, line }));
  return { missingInEnv: missing(example, env), missingInExample: missing(env, example) };
}

/**
 * A .env.example built from a .env: same comments, blank lines and keys, with
 * every value removed so no secret is copied into a file that gets committed.
 */
export function exampleFromEnv(envText: string): string {
  return envText
    .split(/(\r?\n)/)
    .map((part) => {
      const trimmed = part.trim();
      if (!trimmed || trimmed.startsWith("#") || !part.includes("=")) {
        return part;
      }
      return part.slice(0, part.indexOf("=") + 1).trimStart();
    })
    .join("");
}

/** Text to append to a file so it ends with `KEY=` on its own line. */
export function appendKeyText(currentText: string, key: string): string {
  const prefix = currentText === "" || currentText.endsWith("\n") ? "" : "\n";
  return `${prefix}${key}=\n`;
}
