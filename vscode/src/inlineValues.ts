import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import { summarize } from "./sirenCalls";

interface SirenEvent {
  file: string;
  line: number;
  name: string;
  value: string;
  label?: string | null;
  ts: string;
}

const HISTORY = 5;

/** Same file, same key: Windows paths are case-insensitive. */
export function fileKey(file: string): string {
  const normalized = path.normalize(file);
  return process.platform === "win32" ? normalized.toLowerCase() : normalized;
}
const key = fileKey;

/**
 * Tails the events file the Python runtime appends to and shows each
 * siren() call's latest value at the end of its line, GitLens-style.
 */
export class InlineValues implements vscode.Disposable {
  private readonly decoration = vscode.window.createTextEditorDecorationType({
    after: {
      color: new vscode.ThemeColor("siren.inlineValueForeground"),
      margin: "0 0 0 2em",
      fontStyle: "italic",
    },
    rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
  });
  /** file key -> 1-based line -> recent events (newest last) */
  private readonly values = new Map<string, Map<number, SirenEvent[]>>();
  private readonly disposables: vscode.Disposable[] = [];
  private readonly changed = new vscode.EventEmitter<void>();
  /** Fires when captured values are added or cleared. */
  readonly onDidChange = this.changed.event;
  private offset = 0;
  private partial = "";
  /** How many values have been captured since VS Code started. */
  captured = 0;

  /** Latest value captured at a 1-based line of a file, if that line has run. */
  lastValue(file: string, line: number): { name: string; value: string } | undefined {
    const history = this.values.get(key(file))?.get(line);
    return history?.[history.length - 1];
  }

  constructor(
    private readonly eventsFile: string,
    private readonly output: vscode.OutputChannel,
  ) {
    fs.watchFile(eventsFile, { interval: 250 }, () => this.readNew());
    this.disposables.push(
      vscode.window.onDidChangeVisibleTextEditors(() => this.render()),
      vscode.workspace.onDidChangeTextDocument((e) => {
        // Line numbers no longer match what ran; drop that file's values.
        if (e.contentChanges.length && this.values.delete(key(e.document.uri.fsPath))) {
          this.render();
        }
      }),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("siren.inlineValues")) {
          this.render();
        }
      }),
    );
  }

  clear(): void {
    this.values.clear();
    this.render();
  }

  private readNew(): void {
    let size: number;
    try {
      size = fs.statSync(this.eventsFile).size;
    } catch {
      return;
    }
    if (size < this.offset) {
      this.offset = 0; // file was truncated
      this.partial = "";
    }
    if (size === this.offset) {
      return;
    }
    const fd = fs.openSync(this.eventsFile, "r");
    try {
      const buffer = Buffer.alloc(size - this.offset);
      fs.readSync(fd, buffer, 0, buffer.length, this.offset);
      this.offset = size;
      const text = this.partial + buffer.toString("utf8");
      const lines = text.split("\n");
      this.partial = lines.pop() ?? "";
      for (const line of lines) {
        if (line.trim()) {
          this.add(line);
        }
      }
    } finally {
      fs.closeSync(fd);
    }
    this.render();
  }

  private add(raw: string): void {
    let event: SirenEvent;
    try {
      event = JSON.parse(raw);
    } catch {
      return;
    }
    const fileValues = this.values.get(key(event.file)) ?? new Map<number, SirenEvent[]>();
    this.values.set(key(event.file), fileValues);
    const history = fileValues.get(event.line) ?? [];
    history.push(event);
    if (history.length > HISTORY) {
      history.shift();
    }
    fileValues.set(event.line, history);
    this.captured++;

    const label = event.label ? ` [${event.label}]` : "";
    this.output.appendLine(
      `[${event.ts}] ${vscode.workspace.asRelativePath(event.file)}:${event.line}${label} ${event.name} = ${event.value}`,
    );
  }

  private render(): void {
    this.changed.fire();
    const show = vscode.workspace.getConfiguration("siren").get<boolean>("inlineValues", true);
    for (const editor of vscode.window.visibleTextEditors) {
      const fileValues = show ? this.values.get(key(editor.document.uri.fsPath)) : undefined;
      const options: vscode.DecorationOptions[] = [];
      for (const [line, history] of fileValues ?? []) {
        if (line - 1 >= editor.document.lineCount) {
          continue;
        }
        const last = history[history.length - 1];
        const end = editor.document.lineAt(line - 1).range.end;
        const repeat = history.length > 1 ? ` (last of ${history.length})` : "";
        const hover = new vscode.MarkdownString();
        for (const e of history.slice().reverse()) {
          hover.appendMarkdown(`**${e.name}** · ${e.ts}${e.label ? ` · ${e.label}` : ""}\n`);
          hover.appendCodeblock(e.value, "python");
        }
        options.push({
          range: new vscode.Range(end, end),
          hoverMessage: hover,
          renderOptions: {
            after: { contentText: `🧜 ${last.name} = ${summarize(last.value)}${repeat}` },
          },
        });
      }
      editor.setDecorations(this.decoration, options);
    }
  }

  dispose(): void {
    fs.unwatchFile(this.eventsFile);
    this.decoration.dispose();
    this.changed.dispose();
    this.disposables.forEach((d) => d.dispose());
  }
}
