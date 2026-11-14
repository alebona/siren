import * as os from "node:os";
import * as path from "node:path";
import * as vscode from "vscode";
import { callBridge } from "./python";
import { Runtime } from "./runtime";
import { isInside } from "./snippets";
import { validateName } from "./snippetText";

interface SavedRequest {
  name: string;
  method: string;
  url: string;
  path: string;
}

interface RequestSpec {
  method: string;
  url: string;
  headers?: Record<string, string>;
  json?: unknown;
  data?: string | null;
}

interface Response {
  status: number;
  reason: string;
  headers: [string, string][];
  body: string;
}

const REQUESTS_DIR = path.join(os.homedir(), ".siren", "http_collections");
const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"];
const SCHEME = "siren-http";

/** Saved requests in the sidebar; responses open read-only beside the editor. */
export class RequestsView
  implements vscode.TreeDataProvider<SavedRequest>, vscode.TextDocumentContentProvider, vscode.CodeLensProvider, vscode.Disposable
{
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.changed.event;
  private readonly responses = new Map<string, string>();
  private counter = 0;
  private readonly disposables: vscode.Disposable[] = [];

  constructor(private readonly runtime: Runtime) {
    this.disposables.push(
      this.changed,
      vscode.window.registerTreeDataProvider("siren.requests", this),
      vscode.workspace.registerTextDocumentContentProvider(SCHEME, this),
      vscode.languages.registerCodeLensProvider(
        { scheme: "file", pattern: new vscode.RelativePattern(vscode.Uri.file(REQUESTS_DIR), "*.json") },
        this,
      ),
      vscode.workspace.onDidSaveTextDocument((doc) => {
        if (isInside(doc.uri.fsPath, REQUESTS_DIR)) {
          this.changed.fire();
        }
      }),
      vscode.commands.registerCommand("siren.http.refresh", () => this.changed.fire()),
      vscode.commands.registerCommand("siren.http.new", () => this.newRequest()),
      vscode.commands.registerCommand("siren.http.send", (r: SavedRequest) => this.sendSaved(r)),
      vscode.commands.registerCommand("siren.http.edit", (r: SavedRequest) => vscode.window.showTextDocument(vscode.Uri.file(r.path))),
      vscode.commands.registerCommand("siren.http.delete", (r: SavedRequest) => this.remove(r)),
      vscode.commands.registerCommand("siren.http.sendFile", (uri: vscode.Uri) => this.sendFile(uri)),
    );
  }

  async getChildren(): Promise<SavedRequest[]> {
    try {
      return await callBridge<SavedRequest[]>(this.runtime, "http_list");
    } catch {
      return [];
    }
  }

  getTreeItem(r: SavedRequest): vscode.TreeItem {
    const item = new vscode.TreeItem(r.name);
    item.description = `${r.method} ${r.url}`;
    item.tooltip = `${r.method} ${r.url}\nClick to send.`;
    item.iconPath = new vscode.ThemeIcon("globe");
    item.contextValue = "sirenRequest";
    item.command = { command: "siren.http.send", title: "Send", arguments: [r] };
    return item;
  }

  provideTextDocumentContent(uri: vscode.Uri): string {
    return this.responses.get(uri.query) ?? "";
  }

  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    return [
      new vscode.CodeLens(new vscode.Range(0, 0, 0, 0), {
        title: "$(play) Send request",
        command: "siren.http.sendFile",
        arguments: [document.uri],
      }),
    ];
  }

  private async newRequest(): Promise<void> {
    const method = await vscode.window.showQuickPick(METHODS, { title: "New request: method" });
    if (!method) {
      return;
    }
    const url = await vscode.window.showInputBox({
      title: `${method}: URL`,
      placeHolder: "https://api.example.com/items",
      validateInput: (v) => (/^https?:\/\/\S+$/.test(v.trim()) ? undefined : "Enter an http:// or https:// URL."),
    });
    if (!url) {
      return;
    }
    const spec: RequestSpec = { method, url: url.trim() };
    if (["POST", "PUT", "PATCH"].includes(method)) {
      const body = await vscode.window.showInputBox({
        title: `${method} ${spec.url}: JSON body`,
        prompt: "Optional. Leave empty for no body.",
        placeHolder: '{"name": "x"}',
        validateInput: (v) => {
          if (!v.trim()) {
            return undefined;
          }
          try {
            JSON.parse(v);
            return undefined;
          } catch {
            return "Not valid JSON.";
          }
        },
      });
      if (body === undefined) {
        return;
      }
      if (body.trim()) {
        spec.json = JSON.parse(body);
      }
    }
    const sent = await this.send(spec, `${method} ${spec.url}`);
    if (!sent) {
      return;
    }
    const choice = await vscode.window.showInformationMessage(`Siren: ${method} ${spec.url}`, "Save request");
    if (choice === "Save request") {
      const name = await vscode.window.showInputBox({ title: "Save request as", validateInput: validateName });
      if (name) {
        await callBridge(this.runtime, "http_save", { name, ...spec });
        this.changed.fire();
      }
    }
  }

  private async sendSaved(r: SavedRequest): Promise<void> {
    try {
      const spec = await callBridge<RequestSpec>(this.runtime, "http_load", { name: r.name });
      await this.send(spec, r.name);
    } catch (error) {
      vscode.window.showErrorMessage(`Siren: ${(error as Error).message}`);
    }
  }

  private async sendFile(uri: vscode.Uri): Promise<void> {
    const doc = await vscode.workspace.openTextDocument(uri);
    let spec: RequestSpec;
    try {
      spec = JSON.parse(doc.getText());
    } catch {
      vscode.window.showErrorMessage("Siren: this request file isn't valid JSON.");
      return;
    }
    if (!spec.method || !spec.url) {
      vscode.window.showErrorMessage('Siren: a request needs "method" and "url".');
      return;
    }
    await this.send(spec, path.basename(uri.fsPath, ".json"));
  }

  private async send(spec: RequestSpec, title: string): Promise<boolean> {
    let response: Response;
    try {
      response = await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: `Siren: ${spec.method} ${spec.url}` },
        () => callBridge<Response>(this.runtime, "http_send", { ...spec }),
      );
    } catch (error) {
      vscode.window.showErrorMessage(`Siren: request failed: ${(error as Error).message}`);
      return false;
    }
    const { text, json } = formatResponse(spec, response);
    const id = String(++this.counter);
    this.responses.set(id, text);
    const uri = vscode.Uri.from({ scheme: SCHEME, path: `/${title.replace(/[\\/]/g, "_")} (${response.status}).${json ? "jsonc" : "txt"}`, query: id });
    const doc = await vscode.workspace.openTextDocument(uri);
    await vscode.languages.setTextDocumentLanguage(doc, json ? "jsonc" : "plaintext");
    await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside, preview: true });
    return true;
  }

  private async remove(r: SavedRequest): Promise<void> {
    const choice = await vscode.window.showWarningMessage(`Delete request "${r.name}"?`, { modal: true }, "Delete");
    if (choice === "Delete") {
      await callBridge(this.runtime, "http_remove", { name: r.name });
      this.changed.fire();
    }
  }

  dispose(): void {
    this.disposables.forEach((d) => d.dispose());
  }
}

/** Status and headers as comments above the body; JSON bodies pretty-printed. */
export function formatResponse(spec: RequestSpec, r: Response): { text: string; json: boolean } {
  let body = r.body;
  let json = false;
  try {
    body = JSON.stringify(JSON.parse(r.body), null, 2);
    json = true;
  } catch {
    // not JSON: show as-is
  }
  const c = json ? "// " : "";
  const head = [
    `${c}${spec.method} ${spec.url}`,
    `${c}HTTP ${r.status} ${r.reason}`.trimEnd(),
    ...r.headers.map(([k, v]) => `${c}${k}: ${v}`),
    "",
  ];
  return { text: head.join("\n") + "\n" + body + "\n", json };
}
