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

  await check("Ctrl+Alt+S with nothing under the cursor adds siren() and puts the cursor inside", async () => {
    const file = path.join(ws, "empty-insert.py");
    fs.writeFileSync(file, "from siren import siren\nx = 1\n\ntotal = x + 1\nif x:\n    pass\n");
    const editor = await vscode.window.showTextDocument(await vscode.workspace.openTextDocument(file));
    try {
      // Blank line: inserted right there, cursor between the parentheses.
      editor.selection = new vscode.Selection(2, 0, 2, 0);
      await vscode.commands.executeCommand("siren.insert");
      assert.equal(editor.document.lineAt(2).text, "siren()");
      assert.deepEqual([editor.selection.active.line, editor.selection.active.character], [2, 6]);
      await editor.edit((b) => b.insert(editor.selection.active, "x * 2"));
      assert.equal(editor.document.lineAt(2).text, "siren(x * 2)");
      await vscode.commands.executeCommand("leaveSnippet");

      // On a variable: new line below, the name pre-filled and selected.
      editor.selection = new vscode.Selection(3, 1, 3, 1);
      await vscode.commands.executeCommand("siren.insert");
      assert.equal(editor.document.lineAt(4).text, "siren(total)");
      assert.equal(editor.document.getText(editor.selection), "total");
      await vscode.commands.executeCommand("leaveSnippet");

      // On a keyword ("if"): nothing pre-filled, and indented into the block.
      editor.selection = new vscode.Selection(5, 0, 5, 0);
      await vscode.commands.executeCommand("siren.insert");
      assert.equal(editor.document.lineAt(6).text, "    siren()");
    } finally {
      await vscode.commands.executeCommand("leaveSnippet");
      await vscode.commands.executeCommand("workbench.action.revertAndCloseActiveEditor");
    }
  });

  await check("every Actions panel item runs a registered command", async () => {
    const { GROUPS } = await import("../actions");
    const registered = new Set(await vscode.commands.getCommands(true));
    const missing = GROUPS.flatMap((g) => g.actions.map((a) => a.command)).filter((c) => !registered.has(c));
    assert.deepEqual(missing, []);
  });

  await check("Calls counts siren() in every file, open or not, and follows edits", async () => {
    const count = () => vscode.commands.executeCommand<number>("siren._workspaceCallCount");
    // On a timeout, say what the list actually holds, so a CI failure explains itself.
    const expectCount = async (expected: number, what: string) => {
      try {
        await waitFor(async () => ((await count()) === expected ? true : undefined), what);
      } catch {
        const entries = await vscode.commands.executeCommand<string[]>("siren._workspaceCalls");
        throw new Error(`timed out waiting for ${what}: expected ${expected}, got ${await count()} [${entries.join(" ")}]`);
      }
    };
    const before = await count();
    fs.mkdirSync(path.join(ws, "pkg"), { recursive: true });
    fs.writeFileSync(path.join(ws, "pkg", "a.py"), "x = 1\nsiren(x)\nsiren(x, label='again')\n");
    fs.writeFileSync(path.join(ws, "pkg", "b.py"), "y = 2\nsiren(y)\n");
    fs.mkdirSync(path.join(ws, ".venv", "lib"), { recursive: true });
    fs.writeFileSync(path.join(ws, ".venv", "lib", "dep.py"), "siren(1)\n"); // ignored
    await expectCount(before + 3, "new files to be counted");

    // Unsaved edits count too.
    const doc = await vscode.workspace.openTextDocument(path.join(ws, "pkg", "b.py"));
    const editor = await vscode.window.showTextDocument(doc);
    const applied = await editor.edit((b) => b.insert(new vscode.Position(2, 0), "siren(y * 2)\n"));
    assert.ok(applied, `the edit wasn't applied; b.py is ${JSON.stringify(doc.getText())}`);
    await expectCount(before + 4, `an unsaved edit to be counted (b.py: ${JSON.stringify(doc.getText())})`);

    fs.rmSync(path.join(ws, "pkg", "a.py"));
    await expectCount(before + 2, "a deleted file to be dropped");

    // Deleting a whole folder drops everything under it.
    await vscode.commands.executeCommand("workbench.action.closeAllEditors");
    fs.rmSync(path.join(ws, "pkg"), { recursive: true, force: true });
    await expectCount(before, "a deleted folder to be dropped");
  });

  await check("Run current file captures values with no setup", async () => {
    const captured = () => vscode.commands.executeCommand<number>("siren._capturedCount");
    const before = await captured();
    const file = path.join(ws, "run me.py"); // a space in the path, on purpose
    fs.writeFileSync(file, "total = sum([1, 2, 3])\nsiren(total)\n");
    await vscode.window.showTextDocument(await vscode.workspace.openTextDocument(file));
    await vscode.commands.executeCommand("siren.runFile");
    await waitFor(async () => ((await captured()) > before ? true : undefined), "the run to report a value", 60000);
  });

  await check("Enable for this environment: siren() works in a process started outside VS Code", async () => {
    const { execFileSync } = await import("node:child_process");
    const venv = path.join(ws, ".venv-enable");
    const system = process.platform === "win32" ? "python" : "python3";
    execFileSync(system, ["-m", "venv", venv]);
    const venvPython = path.join(venv, process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
    const config = vscode.workspace.getConfiguration("siren");
    await config.update("pythonPath", venvPython, vscode.ConfigurationTarget.Workspace);
    // A process with none of VS Code's variables, like a server or an AI
    // assistant would start.
    const cleanEnv = { ...process.env };
    delete cleanEnv.PYTHONPATH;
    delete cleanEnv.SIREN_VSCODE_EVENTS;
    const script = path.join(ws, "outside.py");
    fs.writeFileSync(script, "siren(6 * 7)\nprint('ran')\n");
    const captured = () => vscode.commands.executeCommand<number>("siren._capturedCount");
    try {
      const before = await captured();
      await vscode.commands.executeCommand("siren.enableEnvironment");
      const out = execFileSync(venvPython, [script], { env: cleanEnv }).toString();
      assert.match(out, /ran/);
      await waitFor(async () => ((await captured()) > before ? true : undefined), "the value from outside VS Code");

      await vscode.commands.executeCommand("siren.disableEnvironment");
      assert.throws(() => execFileSync(venvPython, [script], { env: cleanEnv, stdio: "pipe" }), /NameError/);
    } finally {
      await config.update("pythonPath", undefined, vscode.ConfigurationTarget.Workspace);
    }
  });

  console.log(["Siren integration suite:", ...results].join("\n"));
  if (failed) {
    throw new Error("integration suite failed");
  }
}
