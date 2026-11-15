import * as fs from "node:fs";
import * as vscode from "vscode";
import { callBridge } from "./python";
import { Runtime } from "./runtime";

interface Issue {
  line: number;
  kind: string;
  message: string;
  name?: string;
}

interface QualityResult {
  files: { file: string; issues: Issue[] }[];
}

const SEVERITY: Record<string, vscode.DiagnosticSeverity> = {
  "bare-except": vscode.DiagnosticSeverity.Warning,
  debugger: vscode.DiagnosticSeverity.Warning,
  complexity: vscode.DiagnosticSeverity.Warning,
  "unused-import": vscode.DiagnosticSeverity.Information,
  "unused-def": vscode.DiagnosticSeverity.Information,
  todo: vscode.DiagnosticSeverity.Information,
};

/** Runs siren's dead code, lint and complexity checks and shows them in the Problems panel. */
export class QualityChecker implements vscode.Disposable {
  private readonly diagnostics = vscode.languages.createDiagnosticCollection("siren-quality");
  private readonly disposables: vscode.Disposable[] = [];

  constructor(private readonly runtime: Runtime) {
    this.disposables.push(
      vscode.workspace.onDidSaveTextDocument((doc) => this.onDocument(doc)),
      vscode.workspace.onDidOpenTextDocument((doc) => this.onDocument(doc)),
      vscode.workspace.onDidDeleteFiles((e) => e.files.forEach((uri) => this.diagnostics.delete(uri))),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("siren.quality")) {
          this.diagnostics.clear();
          vscode.workspace.textDocuments.forEach((doc) => this.onDocument(doc));
        }
      }),
    );
    vscode.workspace.textDocuments.forEach((doc) => this.onDocument(doc));
  }

  private onDocument(doc: vscode.TextDocument): void {
    if (doc.languageId === "python" && doc.uri.scheme === "file" && enabled()) {
      this.check(doc.uri.fsPath).catch(() => undefined); // a file that doesn't parse just has no results
    }
  }

  /** Check a file or folder; replaces the diagnostics of every file it scanned. */
  async check(path: string): Promise<number> {
    const threshold = vscode.workspace.getConfiguration("siren").get<number>("quality.complexityThreshold", 10);
    const result = await callBridge<QualityResult>(this.runtime, "quality", { path, threshold });
    let total = 0;
    for (const { file, issues } of result.files) {
      const uri = vscode.Uri.file(file);
      const lines = readLines(file);
      this.diagnostics.set(uri, issues.map((issue) => toDiagnostic(issue, lines)));
      total += issues.length;
    }
    return total;
  }

  /** Check the active Python file now and say what was found. */
  async checkActiveFile(): Promise<void> {
    const doc = vscode.window.activeTextEditor?.document;
    if (!doc || doc.languageId !== "python" || doc.isUntitled) {
      vscode.window.showInformationMessage("Siren: open a saved Python file to check it.");
      return;
    }
    if (doc.isDirty) {
      await doc.save(); // the check reads the file from disk
    }
    const name = doc.uri.path.split("/").pop();
    try {
      const total = await this.check(doc.uri.fsPath);
      if (total === 0) {
        vscode.window.showInformationMessage(`Siren: no code quality issues in ${name}.`);
      } else {
        vscode.commands.executeCommand("workbench.actions.view.problems");
        vscode.window.setStatusBarMessage(`Siren: ${total} issue${total === 1 ? "" : "s"} in ${name}`, 5000);
      }
    } catch (error) {
      vscode.window.showErrorMessage(`Siren: couldn't check ${name}: ${(error as Error).message}`);
    }
  }

  async checkWorkspace(): Promise<void> {
    const folders = vscode.workspace.workspaceFolders ?? [];
    if (!folders.length) {
      vscode.window.showInformationMessage("Siren: open a folder first.");
      return;
    }
    try {
      const total = await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "Siren: checking code quality…" },
        async () => {
          let sum = 0;
          for (const folder of folders) {
            sum += await this.check(folder.uri.fsPath);
          }
          return sum;
        },
      );
      if (total === 0) {
        vscode.window.showInformationMessage("Siren: no code quality issues found.");
      } else {
        vscode.commands.executeCommand("workbench.actions.view.problems");
      }
    } catch (error) {
      vscode.window.showErrorMessage(`Siren: ${(error as Error).message}`);
    }
  }

  dispose(): void {
    this.diagnostics.dispose();
    this.disposables.forEach((d) => d.dispose());
  }
}

function enabled(): boolean {
  return vscode.workspace.getConfiguration("siren").get<boolean>("quality.enabled", true);
}

function readLines(file: string): string[] {
  try {
    return fs.readFileSync(file, "utf8").split(/\r?\n/);
  } catch {
    return [];
  }
}

function toDiagnostic(issue: Issue, lines: string[]): vscode.Diagnostic {
  const index = Math.max(issue.line - 1, 0);
  const text = lines[index] ?? "";
  let start = text.length - text.trimStart().length;
  let end = text.trimEnd().length;
  // Point at the name itself when we know it (unused import, def, complex function).
  if (issue.name) {
    const at = text.search(new RegExp(`\\b${escapeRegExp(issue.name)}\\b`));
    if (at >= 0) {
      start = at;
      end = at + issue.name.length;
    }
  }
  const diagnostic = new vscode.Diagnostic(
    new vscode.Range(index, start, index, Math.max(end, start)),
    issue.message,
    SEVERITY[issue.kind] ?? vscode.DiagnosticSeverity.Information,
  );
  diagnostic.source = "siren";
  diagnostic.code = issue.kind;
  if (issue.kind === "unused-import" || issue.kind === "unused-def") {
    diagnostic.tags = [vscode.DiagnosticTag.Unnecessary];
  }
  return diagnostic;
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
