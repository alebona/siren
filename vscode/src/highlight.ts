import * as vscode from "vscode";
import { findSirenLines } from "./sirenCalls";
import { WorkspaceCalls } from "./workspaceCalls";

/**
 * Highlights siren() lines and shows the counts in the status bar: this
 * file's and the whole workspace's ("🧜 2 · 7").
 */
export class CallHighlighter implements vscode.Disposable {
  private readonly decoration = vscode.window.createTextEditorDecorationType({
    isWholeLine: true,
    backgroundColor: new vscode.ThemeColor("siren.callBackground"),
    overviewRulerColor: new vscode.ThemeColor("siren.inlineValueForeground"),
    overviewRulerLane: vscode.OverviewRulerLane.Left,
  });
  private readonly status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  private readonly disposables: vscode.Disposable[] = [];
  private timer: NodeJS.Timeout | undefined;

  constructor(private readonly workspace: WorkspaceCalls) {
    this.disposables.push(
      workspace.onDidChange(() => this.schedule()),
      vscode.window.onDidChangeVisibleTextEditors(() => this.schedule()),
      vscode.window.onDidChangeActiveTextEditor(() => this.schedule()),
      vscode.workspace.onDidChangeTextDocument(() => this.schedule()),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("siren.highlightCalls")) {
          this.schedule();
        }
      }),
    );
    this.update();
  }

  private schedule(): void {
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.update(), 150);
  }

  private update(): void {
    const on = vscode.workspace.getConfiguration("siren").get<boolean>("highlightCalls", true);
    for (const editor of vscode.window.visibleTextEditors) {
      const ranges =
        on && editor.document.languageId === "python"
          ? findSirenLines(editor.document.getText()).map((l) => editor.document.lineAt(l).range)
          : [];
      editor.setDecorations(this.decoration, ranges);
    }

    const active = vscode.window.activeTextEditor;
    const here =
      on && active?.document.languageId === "python" ? findSirenLines(active.document.getText()).length : 0;
    const total = on ? Math.max(this.workspace.total(), here) : 0;
    const plural = (n: number) => `${n} siren() call${n === 1 ? "" : "s"}`;
    if (here > 0) {
      // Click removes this file's calls, as before.
      this.status.text = total > here ? `🧜 ${here} · ${total}` : `🧜 ${here}`;
      this.status.tooltip =
        `${plural(here)} in this file` +
        (total > here ? `, ${total} in the workspace (see Siren → Calls)` : "") +
        ". Click to remove this file's calls.";
      this.status.command = "siren.cleanFile";
      this.status.show();
    } else if (total > 0) {
      // Nothing in this file, but some elsewhere: click lists them.
      this.status.text = `🧜 ${total}`;
      this.status.tooltip = `${plural(total)} in the workspace, none in this file. Click to see them.`;
      this.status.command = "siren.calls.focus";
      this.status.show();
    } else {
      this.status.hide();
    }
  }

  dispose(): void {
    clearTimeout(this.timer);
    this.decoration.dispose();
    this.status.dispose();
    this.disposables.forEach((d) => d.dispose());
  }
}
