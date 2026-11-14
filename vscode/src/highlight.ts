import * as vscode from "vscode";
import { findSirenLines } from "./sirenCalls";

/** Highlights siren() lines and shows the active file's count in the status bar. */
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

  constructor() {
    this.status.command = "siren.cleanFile";
    this.disposables.push(
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
    const count =
      on && active?.document.languageId === "python" ? findSirenLines(active.document.getText()).length : 0;
    if (count > 0) {
      this.status.text = `🧜 ${count}`;
      this.status.tooltip = `${count} line${count === 1 ? "" : "s"} with siren() in this file. Click to remove them.`;
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
