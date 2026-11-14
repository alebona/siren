import * as os from "node:os";
import * as path from "node:path";
import * as vscode from "vscode";
import { callBridge } from "./python";
import { Runtime } from "./runtime";
import { parseTags, toSnippetSyntax, validateName } from "./snippetText";

interface Snippet {
  name: string;
  tags: string[];
  content: string;
  path: string;
  updated_at?: string;
}

export const SNIPPETS_DIR = path.join(os.homedir(), ".siren", "snippets");

/** Sidebar tree of saved snippets: click inserts at the cursor. */
export class SnippetsView implements vscode.TreeDataProvider<Snippet>, vscode.Disposable {
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.changed.event;
  private filter = "";
  private readonly disposables: vscode.Disposable[] = [];
  private readonly view: vscode.TreeView<Snippet>;

  constructor(private readonly runtime: Runtime) {
    this.view = vscode.window.createTreeView("siren.snippets", { treeDataProvider: this });
    this.disposables.push(
      this.view,
      this.changed,
      // Edited in the editor (snippets are plain files): refresh the tree.
      vscode.workspace.onDidSaveTextDocument((doc) => {
        if (isInside(doc.uri.fsPath, SNIPPETS_DIR)) {
          this.refresh();
        }
      }),
      vscode.commands.registerCommand("siren.snippets.refresh", () => this.refresh()),
      vscode.commands.registerCommand("siren.snippets.search", () => this.search()),
      vscode.commands.registerCommand("siren.snippets.add", () => this.add()),
      vscode.commands.registerCommand("siren.snippets.insert", (s: Snippet) => this.insert(s)),
      vscode.commands.registerCommand("siren.snippets.copy", (s: Snippet) => this.copy(s)),
      vscode.commands.registerCommand("siren.snippets.edit", (s: Snippet) => vscode.window.showTextDocument(vscode.Uri.file(s.path))),
      vscode.commands.registerCommand("siren.snippets.tags", (s: Snippet) => this.editTags(s)),
      vscode.commands.registerCommand("siren.snippets.rename", (s: Snippet) => this.rename(s)),
      vscode.commands.registerCommand("siren.snippets.delete", (s: Snippet) => this.remove(s)),
      vscode.commands.registerCommand("siren.snippets.export", () => this.exportAll()),
      vscode.commands.registerCommand("siren.snippets.import", () => this.importAll()),
    );
  }

  refresh(): void {
    this.changed.fire();
  }

  async getChildren(): Promise<Snippet[]> {
    try {
      const all = await callBridge<Snippet[]>(this.runtime, "snippets_list");
      const term = this.filter.toLowerCase();
      this.view.message = this.filter ? `Filtered by "${this.filter}"` : undefined;
      return term
        ? all.filter(
            (s) =>
              s.name.toLowerCase().includes(term) ||
              s.tags.some((t) => t.toLowerCase().includes(term)) ||
              s.content.toLowerCase().includes(term),
          )
        : all;
    } catch (error) {
      this.view.message = `Couldn't load snippets: ${(error as Error).message}`;
      return [];
    }
  }

  getTreeItem(s: Snippet): vscode.TreeItem {
    const item = new vscode.TreeItem(s.name);
    item.description = s.tags.map((t) => `#${t}`).join(" ");
    item.iconPath = new vscode.ThemeIcon("symbol-snippet");
    item.contextValue = "sirenSnippet";
    const tooltip = new vscode.MarkdownString();
    tooltip.appendCodeblock(s.content.split(/\r?\n/).slice(0, 20).join("\n"));
    tooltip.appendMarkdown("\nClick to insert at the cursor.");
    item.tooltip = tooltip;
    item.command = { command: "siren.snippets.insert", title: "Insert", arguments: [s] };
    return item;
  }

  private async search(): Promise<void> {
    const term = await vscode.window.showInputBox({
      title: "Filter snippets",
      prompt: "Matches name, tag or content. Leave empty to show all.",
      value: this.filter,
    });
    if (term !== undefined) {
      this.filter = term.trim();
      this.refresh();
    }
  }

  private async insert(s: Snippet): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      await vscode.env.clipboard.writeText(s.content);
      vscode.window.showInformationMessage(`Siren: no editor open, so "${s.name}" was copied to the clipboard.`);
      return;
    }
    await editor.insertSnippet(new vscode.SnippetString(toSnippetSyntax(s.content)));
    vscode.window.showTextDocument(editor.document, editor.viewColumn);
  }

  private async copy(s: Snippet): Promise<void> {
    await vscode.env.clipboard.writeText(s.content);
    vscode.window.setStatusBarMessage(`Siren: copied "${s.name}"`, 3000);
  }

  private async add(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    const selected = editor && !editor.selection.isEmpty ? editor.document.getText(editor.selection) : "";
    const name = await vscode.window.showInputBox({
      title: selected ? "Save selection as snippet" : "New snippet",
      prompt: "Name. Use {{name}} in the content for fields you fill in when inserting.",
      validateInput: validateName,
    });
    if (!name) {
      return;
    }
    const tags = await vscode.window.showInputBox({ title: `Tags for "${name}"`, prompt: "Comma-separated, optional", placeHolder: "sql, django" });
    if (tags === undefined) {
      return;
    }
    const saved = await this.save(name, selected, parseTags(tags));
    if (saved && !selected) {
      await vscode.window.showTextDocument(vscode.Uri.file(saved));
    }
  }

  private async save(name: string, content: string, tags: string[]): Promise<string | undefined> {
    try {
      const file = await callBridge<string>(this.runtime, "snippets_save", { name, content, tags });
      this.refresh();
      return file;
    } catch (error) {
      if (!/already exists/.test((error as Error).message)) {
        vscode.window.showErrorMessage(`Siren: ${(error as Error).message}`);
        return undefined;
      }
      const choice = await vscode.window.showWarningMessage(`A snippet named "${name}" already exists.`, { modal: true }, "Replace");
      if (choice !== "Replace") {
        return undefined;
      }
      const file = await callBridge<string>(this.runtime, "snippets_save", { name, content, tags, force: true });
      this.refresh();
      return file;
    }
  }

  private async editTags(s: Snippet): Promise<void> {
    const input = await vscode.window.showInputBox({ title: `Tags for "${s.name}"`, prompt: "Comma-separated", value: s.tags.join(", ") });
    if (input !== undefined) {
      await this.run("snippets_set_tags", { name: s.name, tags: parseTags(input) });
    }
  }

  private async rename(s: Snippet): Promise<void> {
    const name = await vscode.window.showInputBox({ title: `Rename "${s.name}"`, value: s.name, validateInput: validateName });
    if (name && name !== s.name) {
      await this.run("snippets_rename", { old: s.name, new: name });
    }
  }

  private async remove(s: Snippet): Promise<void> {
    const choice = await vscode.window.showWarningMessage(`Delete snippet "${s.name}"?`, { modal: true }, "Delete");
    if (choice === "Delete") {
      await this.run("snippets_remove", { name: s.name });
    }
  }

  private async exportAll(): Promise<void> {
    const target = await vscode.window.showSaveDialog({
      defaultUri: vscode.Uri.file(path.join(os.homedir(), "siren-snippets.json")),
      filters: { JSON: ["json"] },
    });
    if (target) {
      const count = await this.run<number>("snippets_export", { path: target.fsPath });
      if (count !== undefined) {
        vscode.window.showInformationMessage(`Siren: exported ${count} snippet(s).`);
      }
    }
  }

  private async importAll(): Promise<void> {
    const [source] = (await vscode.window.showOpenDialog({ filters: { JSON: ["json"] }, canSelectMany: false })) ?? [];
    if (!source) {
      return;
    }
    const result = await this.run<{ imported: number; skipped: string[] }>("snippets_import", { path: source.fsPath });
    if (result) {
      const skipped = result.skipped.length ? ` Skipped ${result.skipped.length} that already exist: ${result.skipped.join(", ")}.` : "";
      vscode.window.showInformationMessage(`Siren: imported ${result.imported} snippet(s).${skipped}`);
    }
  }

  private async run<T>(op: string, args: Record<string, unknown>): Promise<T | undefined> {
    try {
      const result = await callBridge<T>(this.runtime, op, args);
      this.refresh();
      return result;
    } catch (error) {
      vscode.window.showErrorMessage(`Siren: ${(error as Error).message}`);
      return undefined;
    }
  }

  dispose(): void {
    this.disposables.forEach((d) => d.dispose());
  }
}

export function isInside(file: string, dir: string): boolean {
  const rel = path.relative(dir, file);
  return !!rel && !rel.startsWith("..") && !path.isAbsolute(rel);
}
