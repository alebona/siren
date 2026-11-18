import * as fs from "node:fs/promises";
import * as path from "node:path";
import * as vscode from "vscode";
import { InlineValues, fileKey } from "./inlineValues";
import { findSirenLines, summarize } from "./sirenCalls";

export interface Call {
  /** 1-based line number */
  line: number;
  /** the line's code, trimmed */
  text: string;
}

interface FileCalls {
  uri: vscode.Uri;
  calls: Call[];
}

// Folders that hold installed or generated code, not the project's own.
const EXCLUDE = "**/{.venv,venv,env,node_modules,__pycache__,.git,site-packages,.tox,.nox,build,dist}/**";
const MAX_FILES = 20000;

/**
 * Keeps track of every siren() call in the workspace's Python files: scanned
 * once on startup, then kept current from edits (unsaved text included) and
 * file creates, changes and deletes.
 */
export class WorkspaceCalls implements vscode.Disposable {
  private readonly files = new Map<string, FileCalls>();
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChange = this.changed.event;
  private readonly timers = new Map<string, NodeJS.Timeout>();
  /** Bumped on every edit of a file, to tell a stale disk read from a fresh one. */
  private readonly generation = new Map<string, number>();
  private readonly disposables: vscode.Disposable[] = [];

  constructor() {
    // Watch everything, not just *.py: a new folder (git checkout, pull,
    // unzip) can arrive before its files' own events, and a deleted folder
    // may only report itself, not each file inside it.
    const watcher = vscode.workspace.createFileSystemWatcher("**/*");
    this.disposables.push(
      watcher,
      this.changed,
      watcher.onDidCreate((uri) => this.onCreated(uri)),
      watcher.onDidChange((uri) => {
        if (uri.fsPath.endsWith(".py")) {
          this.scanFile(uri);
        }
      }),
      watcher.onDidDelete((uri) => this.onDeleted(uri)),
      vscode.workspace.onDidChangeTextDocument((e) => {
        const doc = e.document;
        if (doc.languageId === "python" && doc.uri.scheme === "file" && e.contentChanges.length) {
          // Mark the edit right away, so a disk read still in flight is dropped.
          const k = fileKey(doc.uri.fsPath);
          this.generation.set(k, (this.generation.get(k) ?? 0) + 1);
          this.debounce(doc.uri, () => this.setFromText(doc.uri, doc.getText()));
        }
      }),
      vscode.workspace.onDidChangeWorkspaceFolders(() => this.scanAll()),
    );
    this.scanAll();
  }

  total(): number {
    let sum = 0;
    for (const f of this.files.values()) {
      sum += f.calls.length;
    }
    return sum;
  }

  /** Files with calls, sorted by path. */
  entries(): FileCalls[] {
    return [...this.files.values()].sort((a, b) => a.uri.fsPath.localeCompare(b.uri.fsPath));
  }

  async scanAll(): Promise<void> {
    const uris = await vscode.workspace.findFiles("**/*.py", EXCLUDE, MAX_FILES);
    this.files.clear();
    // Read in batches so a big project doesn't open thousands of files at once.
    for (let i = 0; i < uris.length; i += 64) {
      await Promise.all(uris.slice(i, i + 64).map((uri) => this.scanFile(uri, false)));
    }
    this.changed.fire();
  }

  private async onCreated(uri: vscode.Uri): Promise<void> {
    if (isExcluded(uri)) {
      return;
    }
    if (uri.fsPath.endsWith(".py")) {
      await this.scanFile(uri);
      return;
    }
    let isDir = false;
    try {
      isDir = (await fs.stat(uri.fsPath)).isDirectory();
    } catch {
      return;
    }
    if (isDir) {
      await this.scanDir(uri);
      // A folder often fills up right after it's created (git checkout, unzip),
      // and the watcher may report only the folder. Look again shortly after.
      setTimeout(() => this.scanDir(uri), 1000);
    }
  }

  private async scanDir(dir: vscode.Uri): Promise<void> {
    const uris = await vscode.workspace.findFiles(new vscode.RelativePattern(dir, "**/*.py"), EXCLUDE, MAX_FILES);
    await Promise.all(uris.map((u) => this.scanFile(u, false)));
    this.changed.fire();
  }

  private onDeleted(uri: vscode.Uri): void {
    // The path may be a file or a whole folder: drop it and anything under it.
    const k = fileKey(uri.fsPath);
    const prefix = k.endsWith(path.sep) ? k : k + path.sep;
    let removed = false;
    for (const existing of [...this.files.keys()]) {
      if (existing === k || existing.startsWith(prefix)) {
        this.files.delete(existing);
        removed = true;
      }
    }
    if (removed) {
      this.changed.fire();
    }
  }

  private async scanFile(uri: vscode.Uri, fire = true): Promise<void> {
    if (isExcluded(uri)) {
      return;
    }
    const k = fileKey(uri.fsPath);
    const startedAt = this.generation.get(k) ?? 0;
    let text: string | undefined = this.openText(uri);
    if (text === undefined) {
      try {
        text = await fs.readFile(uri.fsPath, "utf8");
      } catch {
        return;
      }
      // The read is async: if the file was edited meanwhile, this disk copy
      // is older than what the edit already recorded, so drop it.
      if ((this.generation.get(k) ?? 0) !== startedAt) {
        return;
      }
      // Opened while we were reading: unsaved edits win over the disk.
      text = this.openText(uri) ?? text;
    }
    this.setFromText(uri, text, fire);
  }

  /** Text of the file if it's open in an editor (may hold unsaved edits). */
  private openText(uri: vscode.Uri): string | undefined {
    const k = fileKey(uri.fsPath);
    return vscode.workspace.textDocuments.find((d) => fileKey(d.uri.fsPath) === k)?.getText();
  }

  private setFromText(uri: vscode.Uri, text: string, fire = true): void {
    const lines = text.split(/\r?\n/);
    const calls = findSirenLines(text).map((i) => ({ line: i + 1, text: lines[i].trim() }));
    const k = fileKey(uri.fsPath);
    const had = this.files.get(k)?.calls.length ?? 0;
    if (calls.length) {
      this.files.set(k, { uri, calls });
    } else {
      this.files.delete(k);
    }
    if (fire && (calls.length || had)) {
      this.changed.fire();
    }
  }

  private debounce(uri: vscode.Uri, run: () => void): void {
    const k = fileKey(uri.fsPath);
    clearTimeout(this.timers.get(k));
    this.timers.set(k, setTimeout(run, 250));
  }

  dispose(): void {
    this.timers.forEach((t) => clearTimeout(t));
    this.disposables.forEach((d) => d.dispose());
  }
}

function isExcluded(uri: vscode.Uri): boolean {
  return /[\\/](\.venv|venv|env|node_modules|__pycache__|\.git|site-packages|\.tox|\.nox|build|dist)[\\/]/.test(uri.fsPath);
}

type Node = { kind: "file"; entry: FileCalls } | { kind: "call"; uri: vscode.Uri; call: Call };

/** Sidebar list of every siren() call in the workspace, grouped by file. */
export class CallsView implements vscode.TreeDataProvider<Node>, vscode.Disposable {
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.changed.event;
  private readonly view: vscode.TreeView<Node>;
  private readonly disposables: vscode.Disposable[] = [];

  constructor(
    private readonly calls: WorkspaceCalls,
    private readonly inline: InlineValues,
  ) {
    this.view = vscode.window.createTreeView("siren.calls", { treeDataProvider: this });
    this.disposables.push(
      this.view,
      this.changed,
      calls.onDidChange(() => this.refresh()),
      inline.onDidChange(() => this.changed.fire()),
      vscode.commands.registerCommand("siren.calls.refresh", () => calls.scanAll()),
    );
    this.refresh();
  }

  private refresh(): void {
    const total = this.calls.total();
    this.view.badge = total ? { value: total, tooltip: `${total} siren() call${total === 1 ? "" : "s"} in the workspace` } : undefined;
    this.changed.fire();
  }

  getChildren(node?: Node): Node[] {
    if (!node) {
      return this.calls.entries().map((entry) => ({ kind: "file", entry }));
    }
    if (node.kind === "file") {
      return node.entry.calls.map((call) => ({ kind: "call", uri: node.entry.uri, call }));
    }
    return [];
  }

  getTreeItem(node: Node): vscode.TreeItem {
    if (node.kind === "file") {
      const { uri, calls } = node.entry;
      const item = new vscode.TreeItem(uri, vscode.TreeItemCollapsibleState.Expanded);
      const dir = path.dirname(vscode.workspace.asRelativePath(uri, false));
      item.description = `${dir === "." ? "" : dir + "  "}${calls.length}`;
      item.iconPath = vscode.ThemeIcon.File;
      item.contextValue = "sirenCallFile";
      return item;
    }
    const { uri, call } = node;
    const captured = this.inline.lastValue(uri.fsPath, call.line);
    const item = new vscode.TreeItem(call.text.length > 60 ? call.text.slice(0, 59) + "…" : call.text);
    item.description = `L${call.line}${captured ? `  = ${summarize(captured.value, 40)}` : ""}`;
    const tooltip = new vscode.MarkdownString();
    tooltip.appendCodeblock(call.text, "python");
    if (captured) {
      tooltip.appendMarkdown(`Last value of **${captured.name}**:`);
      tooltip.appendCodeblock(captured.value, "python");
    } else {
      tooltip.appendMarkdown("Not run yet.");
    }
    item.tooltip = tooltip;
    item.iconPath = new vscode.ThemeIcon(captured ? "debug-breakpoint-log" : "debug-breakpoint-log-unverified");
    item.command = {
      command: "vscode.open",
      title: "Go to call",
      arguments: [uri, { selection: new vscode.Range(call.line - 1, 0, call.line - 1, 0) }],
    };
    return item;
  }

  dispose(): void {
    this.disposables.forEach((d) => d.dispose());
  }
}
