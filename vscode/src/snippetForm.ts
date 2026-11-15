import * as crypto from "node:crypto";
import * as vscode from "vscode";
import { parseTags, validateName } from "./snippetText";

export interface SnippetData {
  name: string;
  tags: string[];
  content: string;
}

export interface SnippetFormHandlers {
  /** Save the snippet; `original` is the name it had when the form opened (undefined for a new one). Returns an error message to show, or undefined on success. */
  save(data: SnippetData, original: string | undefined): Promise<string | undefined>;
  remove(name: string): Promise<boolean>;
}

/**
 * One form to create or edit a snippet: name, tags and code together, saved
 * with a button or Ctrl+S. Opening the same snippet again reuses its tab.
 */
export class SnippetForm {
  private static readonly open = new Map<string, vscode.WebviewPanel>();

  static show(handlers: SnippetFormHandlers, existing?: SnippetData, initialContent = ""): void {
    const key = existing ? `edit:${existing.name}` : `new:${Date.now()}`;
    const reuse = SnippetForm.open.get(key);
    if (reuse) {
      reuse.reveal();
      return;
    }
    const panel = vscode.window.createWebviewPanel(
      "siren.snippetForm",
      existing ? `Snippet: ${existing.name}` : "New snippet",
      vscode.ViewColumn.Active,
      { enableScripts: true, retainContextWhenHidden: true },
    );
    SnippetForm.open.set(key, panel);
    panel.onDidDispose(() => SnippetForm.open.delete(key));

    const data: SnippetData = existing ?? { name: "", tags: [], content: initialContent };
    panel.webview.html = html(panel.webview, data, !!existing);

    panel.webview.onDidReceiveMessage(async (msg: { type: string; name?: string; tags?: string; content?: string }) => {
      if (msg.type === "save") {
        const name = (msg.name ?? "").trim();
        const invalid = validateName(name);
        if (invalid) {
          panel.webview.postMessage({ type: "error", field: "name", message: invalid });
          return;
        }
        const error = await handlers.save(
          { name, tags: parseTags(msg.tags ?? ""), content: msg.content ?? "" },
          existing?.name,
        );
        if (error) {
          panel.webview.postMessage({ type: "error", field: "name", message: error });
          return;
        }
        vscode.window.setStatusBarMessage(`Siren: saved snippet "${name}"`, 3000);
        panel.dispose();
      } else if (msg.type === "delete" && existing) {
        if (await handlers.remove(existing.name)) {
          panel.dispose();
        }
      }
    });
  }
}

function html(webview: vscode.Webview, data: SnippetData, editing: boolean): string {
  const nonce = crypto.randomBytes(16).toString("base64");
  // Safe to embed in a <script>: "<" can't close the tag once escaped.
  const initial = JSON.stringify({ name: data.name, tags: data.tags.join(", "), content: data.content }).replace(
    /</g,
    "\\u003c",
  );
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); padding: 16px 24px; max-width: 860px; }
  h1 { font-size: 1.3em; font-weight: 600; margin: 0 0 16px; }
  label { display: block; font-weight: 600; margin: 14px 0 6px; }
  input, textarea { width: 100%; box-sizing: border-box; color: var(--vscode-input-foreground); background: var(--vscode-input-background);
    border: 1px solid var(--vscode-input-border, transparent); border-radius: 2px; padding: 6px 8px; font-size: inherit; }
  input:focus, textarea:focus { outline: 1px solid var(--vscode-focusBorder); outline-offset: -1px; }
  textarea { font-family: var(--vscode-editor-font-family); font-size: var(--vscode-editor-font-size); min-height: 260px; resize: vertical; tab-size: 4; white-space: pre; }
  .hint { color: var(--vscode-descriptionForeground); margin-top: 6px; }
  .error { color: var(--vscode-errorForeground); margin-top: 6px; min-height: 1.2em; }
  .actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 18px; }
  button { font-size: inherit; padding: 6px 14px; border: none; border-radius: 2px; cursor: pointer;
    color: var(--vscode-button-foreground); background: var(--vscode-button-background); }
  button:hover { background: var(--vscode-button-hoverBackground); }
  button.secondary { color: var(--vscode-button-secondaryForeground); background: var(--vscode-button-secondaryBackground); }
  button.secondary:hover { background: var(--vscode-button-secondaryHoverBackground); }
  code { font-family: var(--vscode-editor-font-family); }
</style>
</head>
<body>
  <h1>${editing ? "Edit snippet" : "New snippet"}</h1>
  <label for="name">Name</label>
  <input id="name" placeholder="query-users" autocomplete="off">
  <div class="error" id="name-error"></div>
  <label for="tags">Tags</label>
  <input id="tags" placeholder="sql, django" autocomplete="off">
  <div class="hint">Separated by commas. Optional.</div>
  <label for="content">Code</label>
  <textarea id="content" spellcheck="false" placeholder="SELECT * FROM users WHERE id = {{id}}"></textarea>
  <div class="hint">Write <code>{{name}}</code> where a value changes: it becomes a field you fill in and move through with Tab when inserting.</div>
  <div class="actions">
    ${editing ? '<button class="secondary" id="delete">Delete</button>' : ""}
    <button id="save">Save</button>
  </div>
<script nonce="${nonce}">
  const vscode = acquireVsCodeApi();
  const initial = ${initial};
  const $ = (id) => document.getElementById(id);
  $("name").value = initial.name;
  $("tags").value = initial.tags;
  $("content").value = initial.content;
  (initial.name ? $("content") : $("name")).focus();

  function save() {
    $("name-error").textContent = "";
    vscode.postMessage({ type: "save", name: $("name").value, tags: $("tags").value, content: $("content").value });
  }
  $("save").addEventListener("click", save);
  const del = $("delete");
  if (del) del.addEventListener("click", () => vscode.postMessage({ type: "delete" }));

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
  });
  // Tab indents inside the code box instead of leaving it.
  $("content").addEventListener("keydown", (e) => {
    if (e.key !== "Tab" || e.shiftKey) return;
    e.preventDefault();
    const t = e.target, start = t.selectionStart, end = t.selectionEnd;
    t.value = t.value.slice(0, start) + "    " + t.value.slice(end);
    t.selectionStart = t.selectionEnd = start + 4;
  });
  window.addEventListener("message", (e) => {
    if (e.data.type === "error") { $("name-error").textContent = e.data.message; $("name").focus(); }
  });
</script>
</body>
</html>`;
}
