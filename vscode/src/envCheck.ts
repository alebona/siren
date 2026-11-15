import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import { appendKeyText, envDrift } from "./envFile";

const MISSING = "env-missing"; // in .env.example, not set in .env
const UNDOCUMENTED = "env-undocumented"; // in .env, not in .env.example

/**
 * Compares .env with .env.example at the root of each workspace folder and
 * marks the drift in both files, with quick fixes that add the missing key.
 */
export class EnvChecker implements vscode.Disposable, vscode.CodeActionProvider {
  private readonly diagnostics = vscode.languages.createDiagnosticCollection("siren-env");
  private readonly disposables: vscode.Disposable[] = [];

  constructor() {
    const watcher = vscode.workspace.createFileSystemWatcher("**/.env*");
    this.disposables.push(
      watcher,
      watcher.onDidCreate(() => this.refresh()),
      watcher.onDidChange(() => this.refresh()),
      watcher.onDidDelete(() => this.refresh()),
      vscode.workspace.onDidChangeWorkspaceFolders(() => this.refresh()),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("siren.envCheck")) {
          this.refresh();
        }
      }),
      vscode.languages.registerCodeActionsProvider({ scheme: "file", pattern: "**/.env*" }, this, {
        providedCodeActionKinds: [vscode.CodeActionKind.QuickFix],
      }),
    );
    this.refresh();
  }

  /** Check on demand (from the Actions panel) and say what was found. */
  report(): void {
    const { compared, issues } = this.refresh(true);
    if (compared === 0) {
      vscode.window.showInformationMessage(
        "Siren: no workspace folder has both .env and .env.example at its root, so there's nothing to compare.",
      );
    } else if (issues === 0) {
      vscode.window.showInformationMessage("Siren: .env and .env.example have the same keys.");
    } else {
      vscode.commands.executeCommand("workbench.actions.view.problems");
    }
  }

  refresh(force = false): { compared: number; issues: number } {
    this.diagnostics.clear();
    let compared = 0;
    let issues = 0;
    if (!force && !vscode.workspace.getConfiguration("siren").get<boolean>("envCheck.enabled", true)) {
      return { compared, issues };
    }
    for (const folder of vscode.workspace.workspaceFolders ?? []) {
      const examplePath = path.join(folder.uri.fsPath, ".env.example");
      const envPath = path.join(folder.uri.fsPath, ".env");
      const exampleText = read(examplePath);
      const envText = read(envPath);
      if (exampleText === undefined || envText === undefined) {
        continue;
      }
      const drift = envDrift(exampleText, envText);
      compared++;
      issues += drift.missingInEnv.length + drift.missingInExample.length;
      this.diagnostics.set(
        vscode.Uri.file(examplePath),
        drift.missingInEnv.map(({ key, line }) =>
          diagnostic(line, key, `${key} is not set in .env`, vscode.DiagnosticSeverity.Warning, MISSING),
        ),
      );
      this.diagnostics.set(
        vscode.Uri.file(envPath),
        drift.missingInExample.map(({ key, line }) =>
          diagnostic(
            line,
            key,
            `${key} is not in .env.example, so teammates won't know to set it`,
            vscode.DiagnosticSeverity.Information,
            UNDOCUMENTED,
          ),
        ),
      );
    }
    return { compared, issues };
  }

  async provideCodeActions(
    document: vscode.TextDocument,
    _range: vscode.Range,
    context: vscode.CodeActionContext,
  ): Promise<vscode.CodeAction[]> {
    const actions: vscode.CodeAction[] = [];
    const ours = context.diagnostics.filter((d) => d.source === "siren" && (d.code === MISSING || d.code === UNDOCUMENTED));
    for (const diag of ours) {
      const key = keyAt(document, diag.range.start.line);
      const targetName = diag.code === MISSING ? ".env" : ".env.example";
      const target = vscode.Uri.file(path.join(path.dirname(document.uri.fsPath), targetName));
      const targetDoc = await vscode.workspace.openTextDocument(target);
      const end = targetDoc.lineAt(targetDoc.lineCount - 1).range.end;
      const edit = new vscode.WorkspaceEdit();
      edit.insert(target, end, appendKeyText(targetDoc.getText(), key));
      const action = new vscode.CodeAction(`Add ${key}= to ${targetName}`, vscode.CodeActionKind.QuickFix);
      action.edit = edit;
      action.diagnostics = [diag];
      action.isPreferred = true;
      actions.push(action);
    }
    return actions;
  }

  dispose(): void {
    this.diagnostics.dispose();
    this.disposables.forEach((d) => d.dispose());
  }
}

function read(file: string): string | undefined {
  try {
    return fs.readFileSync(file, "utf8");
  } catch {
    return undefined;
  }
}

function keyAt(document: vscode.TextDocument, line: number): string {
  return document.lineAt(line).text.split("=", 1)[0].trim().replace(/^export\s+/, "");
}

function diagnostic(
  line: number,
  key: string,
  message: string,
  severity: vscode.DiagnosticSeverity,
  code: string,
): vscode.Diagnostic {
  const d = new vscode.Diagnostic(new vscode.Range(line, 0, line, key.length), message, severity);
  d.source = "siren";
  d.code = code;
  return d;
}
