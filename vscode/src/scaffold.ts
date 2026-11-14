import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import { callBridge } from "./python";
import { Runtime } from "./runtime";

const TEMPLATES = [
  { label: "script", description: "<name>.py with a main() entry point" },
  { label: "class", description: "<name>.py with a class" },
  { label: "dataclass", description: "<name>.py with a data class (__repr__, __eq__)" },
  { label: "test", description: "test_<name>.py with a unittest TestCase" },
  { label: "package", description: "<name>/ with __init__.py, core.py and tests/" },
];

/** New file or package from a siren template, into the folder that was right-clicked. */
export async function newFromTemplate(runtime: Runtime, target?: vscode.Uri): Promise<void> {
  const base = baseFolder(target);
  if (!base) {
    vscode.window.showInformationMessage("Siren: open a folder first.");
    return;
  }
  const template = await vscode.window.showQuickPick(TEMPLATES, {
    title: `New from template in ${vscode.workspace.asRelativePath(base) || base}`,
  });
  if (!template) {
    return;
  }
  const name = await vscode.window.showInputBox({
    title: `New ${template.label}`,
    prompt: "Name (a Python identifier)",
    placeHolder: template.label === "class" || template.label === "dataclass" ? "Widget" : "my_tool",
    validateInput: (v) => (/^[A-Za-z_][A-Za-z0-9_]*$/.test(v) ? undefined : "Use letters, digits and _, not starting with a digit."),
  });
  if (!name) {
    return;
  }
  try {
    const created = await callBridge<string[]>(runtime, "scaffold", { template: template.label, name, path: base });
    // For a package, open its core module rather than the empty __init__.py.
    const main = created.find((f) => f.endsWith(`${path.sep}core.py`)) ?? created[0];
    await vscode.window.showTextDocument(vscode.Uri.file(main));
  } catch (error) {
    vscode.window.showErrorMessage(`Siren: ${(error as Error).message}`);
  }
}

function baseFolder(target?: vscode.Uri): string | undefined {
  if (target?.scheme === "file") {
    try {
      return fs.statSync(target.fsPath).isDirectory() ? target.fsPath : path.dirname(target.fsPath);
    } catch {
      // fall through
    }
  }
  const active = vscode.window.activeTextEditor?.document.uri;
  const folder = (active && vscode.workspace.getWorkspaceFolder(active)) ?? vscode.workspace.workspaceFolders?.[0];
  return folder?.uri.fsPath;
}
