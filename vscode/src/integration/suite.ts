// Runs inside the extension host started by runTest.ts.
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";

async function waitFor<T>(probe: () => T | undefined | Promise<T | undefined>, what: string, ms = 30000): Promise<T> {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    const value = await probe();
    if (value !== undefined) {
      return value;
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`timed out waiting for ${what}`);
}

const sirenDiagnostics = (uri: vscode.Uri) => vscode.languages.getDiagnostics(uri).filter((d) => d.source === "siren");

export async function run(): Promise<void> {
  const ws = vscode.workspace.workspaceFolders![0].uri.fsPath;
  const ext = vscode.extensions.getExtension("alebona.siren");
  assert.ok(ext, "extension not found");
  await ext.activate();

  const results: string[] = [];
  let failed = false;
  const check = async (name: string, body: () => Promise<void>) => {
    try {
      await body();
      results.push(`  ok   ${name}`);
    } catch (error) {
      failed = true;
      results.push(`  FAIL ${name}: ${(error as Error).message}`);
    }
  };

  await check("code quality issues reach the Problems panel", async () => {
    const file = path.join(ws, "mod.py");
    fs.writeFileSync(file, "import os\n\ndef helper():\n    try:\n        pass\n    except:\n        pass\n");
    const doc = await vscode.workspace.openTextDocument(file);
    await vscode.window.showTextDocument(doc);
    const diags = await waitFor(() => {
      const d = sirenDiagnostics(doc.uri);
      return d.length >= 3 ? d : undefined;
    }, "quality diagnostics");
    assert.deepEqual(diags.map((d) => String(d.code)).sort(), ["bare-except", "unused-def", "unused-import"]);
    const unusedImport = diags.find((d) => d.code === "unused-import")!;
    assert.equal(doc.getText(unusedImport.range), "os");
  });

  await check(".env drift is marked and the quick fix adds the key", async () => {
    fs.writeFileSync(path.join(ws, ".env.example"), "A=\nB=\n");
    fs.writeFileSync(path.join(ws, ".env"), "A=1\nC=2\n");
    const example = vscode.Uri.file(path.join(ws, ".env.example"));
    const env = vscode.Uri.file(path.join(ws, ".env"));
    const missing = await waitFor(() => {
      const d = sirenDiagnostics(example);
      return d.length ? d : undefined;
    }, ".env.example diagnostics");
    assert.equal(missing[0].message, "B is not set in .env");
    assert.equal(missing[0].range.start.line, 1);
    assert.match(sirenDiagnostics(env)[0]?.message ?? "", /^C is not in \.env\.example/);

    await vscode.window.showTextDocument(example);
    const actions = await vscode.commands.executeCommand<vscode.CodeAction[]>(
      "vscode.executeCodeActionProvider",
      example,
      missing[0].range,
    );
    const fix = actions.find((a) => a.title === "Add B= to .env");
    assert.ok(fix?.edit, `quick fix not offered (got: ${actions.map((a) => a.title).join(", ")})`);
    await vscode.workspace.applyEdit(fix.edit);
    const envDoc = await vscode.workspace.openTextDocument(env);
    assert.equal(envDoc.getText(), "A=1\nC=2\nB=\n");
  });

  await check("Ctrl+Alt+S logs the variable under the cursor and adds the import", async () => {
    const file = path.join(ws, "ins.py");
    fs.writeFileSync(file, "x = 1\nprint(x)\n");
    const editor = await vscode.window.showTextDocument(await vscode.workspace.openTextDocument(file));
    editor.selection = new vscode.Selection(0, 0, 0, 0);
    await vscode.commands.executeCommand("siren.insert");
    assert.equal(editor.document.getText(), "from siren import siren\nx = 1\nsiren(x)\nprint(x)\n");
  });

  await check("a new terminal gets the bundled runtime and siren() reports to the editor", async () => {
    const probe = path.join(ws, "probe.py");
    const out = path.join(ws, "probe.json");
    fs.writeFileSync(
      probe,
      [
        "import json, os",
        "answer = 41 + 1",
        "siren(answer)  # no import: sitecustomize made it a builtin",
        "import siren as module",
        "events = os.environ.get('SIREN_VSCODE_EVENTS')",
        `json.dump({'runtime': module.__file__, 'events': open(events).read()}, open(${JSON.stringify(out)}, 'w'))`,
        "",
      ].join("\n"),
    );
    const terminal = vscode.window.createTerminal({ name: "siren-it", cwd: ws });
    terminal.sendText(`python "${probe}"`);
    const result = await waitFor(() => {
      try {
        return JSON.parse(fs.readFileSync(out, "utf8")) as { runtime: string; events: string };
      } catch {
        return undefined;
      }
    }, "the probe script to run in the terminal", 60000);
    terminal.dispose();
    // Windows paths are case-insensitive ("c:\" and "C:\" are the same drive).
    const norm = (p: string) => (process.platform === "win32" ? p.toLowerCase() : p);
    assert.ok(
      norm(result.runtime).startsWith(norm(path.join(ext.extensionPath, "python"))),
      `runtime came from ${result.runtime}`,
    );
    const event = JSON.parse(result.events.trim().split("\n")[0]);
    assert.equal(event.name, "answer");
    assert.equal(event.value, "42");
    assert.equal(event.line, 3);
  });

  await check("every Actions panel item runs a registered command", async () => {
    const { GROUPS } = await import("../actions");
    const registered = new Set(await vscode.commands.getCommands(true));
    const missing = GROUPS.flatMap((g) => g.actions.map((a) => a.command)).filter((c) => !registered.has(c));
    assert.deepEqual(missing, []);
  });

  console.log(["Siren integration suite:", ...results].join("\n"));
  if (failed) {
    throw new Error("integration suite failed");
  }
}
