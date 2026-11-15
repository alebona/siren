import * as path from "node:path";
import * as vscode from "vscode";
import { ActionsView } from "./actions";
import { EnvChecker } from "./envCheck";
import { CallHighlighter } from "./highlight";
import { RequestsView } from "./http";
import { InlineValues } from "./inlineValues";
import { runModule } from "./python";
import { QualityChecker } from "./quality";
import { Runtime } from "./runtime";
import { newFromTemplate } from "./scaffold";
import {
  hasSirenImport,
  importInsertLine,
  indentAfter,
  parseCleanPreview,
  parseRemovedCount,
} from "./sirenCalls";
import { SnippetsView } from "./snippets";

export function activate(context: vscode.ExtensionContext): void {
  const runtime = new Runtime(context);
  const output = vscode.window.createOutputChannel("Siren");
  const inline = new InlineValues(runtime.eventsFile, output);
  const quality = new QualityChecker(runtime);
  const env = new EnvChecker();

  context.subscriptions.push(
    runtime,
    output,
    inline,
    quality,
    env,
    new CallHighlighter(),
    vscode.window.registerTreeDataProvider("siren.actions", new ActionsView()),
    vscode.commands.registerCommand("siren.checkEnv", () => env.report()),
    new SnippetsView(runtime),
    new RequestsView(runtime),
    vscode.commands.registerCommand("siren.insert", insertSiren),
    vscode.commands.registerCommand("siren.cleanFile", () => cleanFile(runtime)),
    vscode.commands.registerCommand("siren.cleanWorkspace", () => cleanWorkspace(runtime)),
    vscode.commands.registerCommand("siren.clearInlineValues", () => inline.clear()),
    vscode.commands.registerCommand("siren.showOutput", () => output.show()),
    vscode.commands.registerCommand("siren.checkQuality", () => quality.checkWorkspace()),
    vscode.commands.registerCommand("siren.newFromTemplate", (uri?: vscode.Uri) => newFromTemplate(runtime, uri)),
  );
}

export function deactivate(): void {}

async function insertSiren(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== "python") {
    return;
  }
  const doc = editor.document;
  const indentUnit = editor.options.insertSpaces
    ? " ".repeat(Number(editor.options.tabSize) || 4)
    : "\t";
  const addImport =
    vscode.workspace.getConfiguration("siren").get<boolean>("addImport", true) &&
    !hasSirenImport(doc.getText());

  // Selections: wrap in place. Empty selection: log the word under the cursor
  // on a new line below.
  const edits: { range: vscode.Range; text: string }[] = [];
  for (const selection of editor.selections) {
    if (!selection.isEmpty) {
      edits.push({ range: selection, text: `siren(${doc.getText(selection)})` });
      continue;
    }
    const wordRange = doc.getWordRangeAtPosition(selection.active, /[\w.]+/);
    if (!wordRange) {
      continue;
    }
    const line = doc.lineAt(selection.active.line);
    const indent = indentAfter(line.text, indentUnit);
    edits.push({
      range: new vscode.Range(line.range.end, line.range.end),
      text: `\n${indent}siren(${doc.getText(wordRange)})`,
    });
  }
  if (!edits.length) {
    vscode.window.showInformationMessage("Siren: select an expression or put the cursor on a variable.");
    return;
  }

  await editor.edit((builder) => {
    for (const edit of edits) {
      builder.replace(edit.range, edit.text);
    }
    if (addImport) {
      const at = new vscode.Position(importInsertLine(doc.getText()), 0);
      builder.insert(at, "from siren import siren\n");
    }
  });
}

async function cleanFile(runtime: Runtime): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== "python") {
    vscode.window.showInformationMessage("Siren: open a Python file first.");
    return;
  }
  const doc = editor.document;
  if (doc.isUntitled) {
    vscode.window.showInformationMessage("Siren: save the file first.");
    return;
  }
  if (doc.isDirty) {
    await doc.save();
  }
  const file = doc.uri.fsPath;
  await runClean(runtime, file, path.dirname(file), doc.uri, path.basename(file));
}

async function cleanWorkspace(runtime: Runtime): Promise<void> {
  const folders = vscode.workspace.workspaceFolders ?? [];
  if (!folders.length) {
    vscode.window.showInformationMessage("Siren: open a folder first.");
    return;
  }
  const folder =
    folders.length === 1
      ? folders[0]
      : await vscode.window.showWorkspaceFolderPick({ placeHolder: "Remove siren() calls from which folder?" });
  if (!folder) {
    return;
  }
  await vscode.workspace.saveAll(false);
  await runClean(runtime, folder.uri.fsPath, folder.uri.fsPath, folder.uri, folder.name);
}

async function runClean(
  runtime: Runtime,
  target: string,
  cwd: string,
  resource: vscode.Uri,
  displayName: string,
): Promise<void> {
  try {
    const dry = await runModule(runtime, "siren.clean", [target, "--dry-run"], cwd, resource);
    const preview = parseCleanPreview(dry.stdout);
    if (preview.total === 0) {
      vscode.window.showInformationMessage(`Siren: no siren() calls in ${displayName}.`);
      return;
    }

    const lines = `${preview.total} line${preview.total === 1 ? "" : "s"}`;
    if (preview.files.length > 1) {
      // Show which files will change before asking.
      const picked = await vscode.window.showQuickPick(
        [
          { label: `$(trash) Remove ${lines} from ${preview.files.length} files`, remove: true },
          ...preview.files.map((f) => ({
            label: vscode.workspace.asRelativePath(path.resolve(cwd, f.path)),
            description: `${f.lines} line${f.lines === 1 ? "" : "s"}`,
            remove: false,
          })),
        ],
        { placeHolder: `siren() calls found in ${displayName}. Pick the first item to remove them all.` },
      );
      if (!picked?.remove) {
        return;
      }
    } else {
      const choice = await vscode.window.showWarningMessage(
        `Remove ${lines} with siren() from ${displayName}?`,
        { modal: true, detail: "A call that is the only line in a block is replaced by `pass`." },
        "Remove",
      );
      if (choice !== "Remove") {
        return;
      }
    }

    const result = await runModule(runtime, "siren.clean", [target], cwd, resource);
    const removed = parseRemovedCount(result.stdout);
    const kept = preview.total - removed;
    const keptNote = " A file is left untouched when removing its calls can't produce valid Python, even with `pass`.";
    if (removed === 0) {
      vscode.window.showWarningMessage(`Siren: nothing was removed from ${displayName}.${keptNote}`);
    } else if (kept > 0) {
      vscode.window.showWarningMessage(
        `Siren: removed ${removed} line(s) from ${displayName}; ${kept} kept.${keptNote}`,
      );
    } else {
      vscode.window.showInformationMessage(`Siren: removed ${removed} line(s) from ${displayName}.`);
    }
  } catch (error) {
    vscode.window.showErrorMessage(`Siren: ${(error as Error).message}`);
  }
}
