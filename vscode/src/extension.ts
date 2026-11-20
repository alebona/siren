import * as path from "node:path";
import * as vscode from "vscode";
import { ActionsView } from "./actions";
import { EnvChecker } from "./envCheck";
import { EnvironmentInstaller } from "./environment";
import { CallHighlighter } from "./highlight";
import { RequestsView } from "./http";
import { InlineValues } from "./inlineValues";
import { resolvePython, runModule } from "./python";
import { QualityChecker } from "./quality";
import { Runtime } from "./runtime";
import { newFromTemplate } from "./scaffold";
import {
  findSirenLines,
  hasSirenImport,
  importInsertLine,
  indentAfter,
  parseCleanPreview,
  parseRemovedCount,
  parseSkipped,
} from "./sirenCalls";
import { SnippetsView } from "./snippets";
import { CallsView, WorkspaceCalls } from "./workspaceCalls";

export function activate(context: vscode.ExtensionContext): void {
  const runtime = new Runtime(context);
  const output = vscode.window.createOutputChannel("Siren");
  const inline = new InlineValues(runtime.eventsFile, output);
  const quality = new QualityChecker(runtime);
  const env = new EnvChecker();
  const calls = new WorkspaceCalls();
  const actions = new ActionsView();
  findManagePy().then((found) => actions.setDjango(found.length > 0));

  context.subscriptions.push(
    runtime,
    output,
    inline,
    quality,
    env,
    calls,
    new CallHighlighter(calls),
    new EnvironmentInstaller(context, runtime),
    new CallsView(calls, inline),
    // Internal: lets the integration tests read the workspace total.
    vscode.commands.registerCommand("siren._workspaceCallCount", () => calls.total()),
    vscode.commands.registerCommand("siren._workspaceCalls", () =>
      calls.entries().map((e) => `${vscode.workspace.asRelativePath(e.uri)}:${e.calls.map((c) => c.line).join(",")}`),
    ),
    vscode.commands.registerCommand("siren._capturedCount", () => inline.captured),
    vscode.window.registerTreeDataProvider("siren.actions", actions),
    vscode.commands.registerCommand("siren.checkEnv", () => env.report()),
    new SnippetsView(runtime),
    new RequestsView(runtime),
    vscode.commands.registerCommand("siren.insert", insertSiren),
    vscode.commands.registerCommand("siren.cleanFile", () => cleanFile(runtime)),
    vscode.commands.registerCommand("siren.cleanWorkspace", () => cleanWorkspace(runtime, calls)),
    vscode.commands.registerCommand("siren.statusMenu", () => statusMenu(calls)),
    vscode.commands.registerCommand("siren.runDjango", () => runDjango(runtime)),
    vscode.commands.registerCommand("siren.clearInlineValues", () => inline.clear()),
    vscode.commands.registerCommand("siren.showOutput", () => showCapturedValues(inline, output)),
    vscode.commands.registerCommand("siren.runFile", (uri?: vscode.Uri) => runFile(runtime, uri)),
    vscode.commands.registerCommand("siren.checkQuality", () => quality.checkWorkspace()),
    vscode.commands.registerCommand("siren.checkQualityFile", () => quality.checkActiveFile()),
    vscode.commands.registerCommand("siren.newFromTemplate", (uri?: vscode.Uri) => newFromTemplate(runtime, uri)),
  );
}

export function deactivate(): void {}

async function showCapturedValues(inline: InlineValues, output: vscode.OutputChannel): Promise<void> {
  output.show(true);
  if (inline.captured > 0) {
    return;
  }
  // An empty channel looks broken: say why, and offer the one-click way in.
  const run = "Run Current File";
  const choice = await vscode.window.showInformationMessage(
    "Siren hasn't captured any values yet. Values come from Python programs started in a VS Code terminal opened after Siren loaded, or with F5. Programs run elsewhere (an older terminal, an external one, or by Claude Code) don't report here.",
    run,
  );
  if (choice === run) {
    await vscode.commands.executeCommand("siren.runFile");
  }
}

/** manage.py files in the workspace, outside virtualenvs and installed packages. */
export async function findManagePy(): Promise<vscode.Uri[]> {
  return vscode.workspace.findFiles(
    "**/manage.py",
    "**/{.venv,venv,env,node_modules,site-packages,.git,.tox}/**",
    10,
  );
}

/**
 * Start the Django dev server in a new terminal with Siren loaded, so every
 * siren() in views, models and the rest reports to the editor. The
 * autoreloader's child process inherits the same environment.
 */
async function runDjango(runtime: Runtime): Promise<void> {
  const found = await findManagePy();
  if (!found.length) {
    vscode.window.showInformationMessage("Siren: no manage.py in this workspace, so it isn't a Django project.");
    return;
  }
  let manage = found[0];
  if (found.length > 1) {
    const pick = await vscode.window.showQuickPick(
      found.map((uri) => ({ label: vscode.workspace.asRelativePath(uri), uri })),
      { placeHolder: "Which Django project?" },
    );
    if (!pick) {
      return;
    }
    manage = pick.uri;
  }
  const python = await resolvePython(manage);
  const args = vscode.workspace.getConfiguration("siren").get<string[]>("django.runserverArgs", ["runserver"]);
  const terminal = vscode.window.createTerminal({
    name: "Siren: Django",
    // Runs python directly (no shell), so paths with spaces need no quoting.
    shellPath: python,
    shellArgs: [manage.fsPath, ...args],
    cwd: path.dirname(manage.fsPath),
    env: runtime.env(),
  });
  terminal.show();
}

/** Run a Python file in a new terminal with the Siren runtime, so its values show up. */
async function runFile(runtime: Runtime, uri?: vscode.Uri): Promise<void> {
  const doc =
    (uri && (await vscode.workspace.openTextDocument(uri))) ||
    (vscode.window.activeTextEditor?.document.languageId === "python" ? vscode.window.activeTextEditor.document : undefined);
  if (!doc || doc.languageId !== "python" || doc.isUntitled) {
    vscode.window.showInformationMessage("Siren: open a saved Python file to run it.");
    return;
  }
  if (doc.isDirty) {
    await doc.save();
  }
  const python = await resolvePython(doc.uri);
  const folder = vscode.workspace.getWorkspaceFolder(doc.uri);
  // Runs python directly (no shell), so paths with spaces need no quoting.
  const terminal = vscode.window.createTerminal({
    name: `Siren: ${path.basename(doc.uri.fsPath)}`,
    shellPath: python,
    shellArgs: [doc.uri.fsPath],
    cwd: folder?.uri.fsPath ?? path.dirname(doc.uri.fsPath),
    env: runtime.env(),
  });
  terminal.show(true);
}

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

  const importEdit = (builder: vscode.TextEditorEdit) => {
    if (addImport) {
      builder.insert(new vscode.Position(importInsertLine(doc.getText()), 0), "from siren import siren\n");
    }
  };

  // Something selected: wrap each selection in siren(...), in place.
  if (editor.selections.some((s) => !s.isEmpty)) {
    await editor.edit((builder) => {
      for (const selection of editor.selections) {
        if (!selection.isEmpty) {
          builder.replace(selection, `siren(${doc.getText(selection)})`);
        }
      }
      importEdit(builder);
    });
    return;
  }

  // Nothing selected: add siren() and leave the cursor between the
  // parentheses. On a blank line it goes right there; otherwise on a new line
  // below. A variable under the cursor comes pre-filled and selected, so
  // typing replaces it.
  if (addImport) {
    await editor.edit(importEdit, { undoStopBefore: true, undoStopAfter: false });
  }
  const cursor = editor.selection.active; // already moved down if the import went above it
  const line = doc.lineAt(cursor.line);
  const wordRange = doc.getWordRangeAtPosition(cursor, /[A-Za-z_][\w.]*/);
  const word = wordRange ? doc.getText(wordRange) : "";
  const inner = word && !PYTHON_KEYWORDS.has(word) ? `\${1:${word}}` : "$1";
  let at = cursor;
  if (!line.isEmptyOrWhitespace) {
    const indent = indentAfter(line.text, indentUnit);
    await editor.edit((builder) => builder.insert(line.range.end, `\n${indent}`), {
      undoStopBefore: !addImport,
      undoStopAfter: false,
    });
    at = new vscode.Position(line.lineNumber + 1, indent.length);
  }
  await editor.insertSnippet(new vscode.SnippetString(`siren(${inner})`), at, {
    undoStopBefore: false,
    undoStopAfter: true,
  });
  // Clicked from the sidebar: bring the focus back to the editor to type.
  await vscode.window.showTextDocument(doc, editor.viewColumn);
}

const PYTHON_KEYWORDS = new Set(
  "and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass print raise return try while with yield True False None".split(
    " ",
  ),
);

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

/**
 * Remove calls from every file the Calls list knows about. Only those files
 * are touched, so a big project (or a virtualenv with an unusual name inside
 * it) doesn't mean walking and parsing thousands of files.
 */
async function cleanWorkspace(runtime: Runtime, calls: WorkspaceCalls): Promise<void> {
  const entries = calls.entries();
  if (!entries.length) {
    vscode.window.showInformationMessage("Siren: no siren() calls in this workspace.");
    return;
  }
  const total = entries.reduce((sum, e) => sum + e.calls.length, 0);
  const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
  const picked = await vscode.window.showQuickPick(
    [
      { label: `$(trash) Remove ${plural(total, "call")} from ${plural(entries.length, "file")}`, remove: true },
      ...entries.map((e) => ({
        label: vscode.workspace.asRelativePath(e.uri),
        description: plural(e.calls.length, "call"),
        remove: false,
      })),
    ],
    { placeHolder: "Files with siren() calls. Pick the first item to remove them all (a call alone in a block becomes pass)." },
  );
  if (!picked?.remove) {
    return;
  }
  await vscode.workspace.saveAll(false);

  const files = entries.map((e) => e.uri.fsPath);
  const BATCH = 40; // keeps each command line well under the Windows length limit
  let removed = 0;
  const skipped: string[] = [];
  try {
    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: "Siren: removing siren() calls", cancellable: false },
      async (progress) => {
        for (let i = 0; i < files.length; i += BATCH) {
          const batch = files.slice(i, i + BATCH);
          progress.report({ message: `${Math.min(i + BATCH, files.length)}/${files.length} files`, increment: (batch.length / files.length) * 100 });
          const cwd = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(batch[0]))?.uri.fsPath ?? path.dirname(batch[0]);
          const result = await runModule(runtime, "siren.clean", batch, cwd, vscode.Uri.file(batch[0]));
          removed += parseRemovedCount(result.stdout);
          skipped.push(...parseSkipped(result.stdout));
        }
      },
    );
  } catch (error) {
    vscode.window.showErrorMessage(`Siren: ${(error as Error).message}`);
    return;
  }
  const done = `Siren: removed ${plural(removed, "line")} from ${plural(files.length, "file")}.`;
  if (skipped.length) {
    vscode.window.showWarningMessage(`${done} Skipped ${plural(skipped.length, "file")}: ${skipped.join("; ")}`);
  } else {
    vscode.window.showInformationMessage(done);
  }
}

/** The status bar 🧜: this file or the whole workspace, or see the list. */
async function statusMenu(calls: WorkspaceCalls): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  const here = editor?.document.languageId === "python" ? findSirenLines(editor.document.getText()).length : 0;
  const total = calls.total();
  const items: (vscode.QuickPickItem & { command: string })[] = [];
  if (here > 0) {
    items.push({
      label: `$(file) Remove from this file`,
      description: `${here} call${here === 1 ? "" : "s"}`,
      command: "siren.cleanFile",
    });
  }
  if (total > 0) {
    items.push({
      label: `$(files) Remove from the whole workspace`,
      description: `${total} call${total === 1 ? "" : "s"} in ${calls.entries().length} file${calls.entries().length === 1 ? "" : "s"}`,
      command: "siren.cleanWorkspace",
    });
  }
  items.push({ label: "$(list-tree) Show all calls", description: "Siren → Calls", command: "siren.calls.focus" });
  const picked = await vscode.window.showQuickPick(items, { placeHolder: "siren() calls" });
  if (picked) {
    await vscode.commands.executeCommand(picked.command);
  }
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
