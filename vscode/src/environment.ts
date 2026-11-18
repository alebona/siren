import { execFile } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import { resolvePython } from "./python";
import { Runtime } from "./runtime";

const PTH_NAME = "siren-vscode.pth";
const STATE_KEY = "siren.enabledEnvironments";

// Finds where this interpreter loads .pth files from: the virtualenv's
// site-packages, or the user's site-packages for a global Python (writable
// without admin rights). Runs on Python 2.7 and 3.
const LOCATE = [
  "import json, site, sys",
  "venv = hasattr(sys, 'real_prefix') or getattr(sys, 'base_prefix', sys.prefix) != sys.prefix",
  "try:",
  "    from distutils.sysconfig import get_python_lib",
  "    purelib = get_python_lib()",
  "except Exception:",
  "    import sysconfig",
  "    purelib = sysconfig.get_paths()['purelib']",
  "user = getattr(site, 'ENABLE_USER_SITE', False) and not venv",
  "target = site.getusersitepackages() if user else purelib",
  "print(json.dumps({'dir': target, 'venv': bool(venv), 'version': sys.version.split()[0], 'exe': sys.executable}))",
].join("\n");

interface Location {
  dir: string;
  venv: boolean;
  version: string;
  exe: string;
}

function locate(python: string): Promise<Location> {
  return new Promise((resolve, reject) => {
    execFile(python, ["-c", LOCATE], { windowsHide: true }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error((stderr || error.message).trim()));
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim().split(/\r?\n/).pop() ?? ""));
      } catch {
        reject(new Error(`unexpected output from ${python}: ${stdout}`));
      }
    });
  });
}

/**
 * The .pth line. Python runs a .pth line that starts with "import" when it
 * starts up, so every process using this environment gets siren as a
 * builtin and reports values to this workspace's editor: terminals outside
 * VS Code, servers, task runners, scripts run by other tools.
 */
function pthLine(runtimeDir: string, eventsFile: string): string {
  const code = [
    "import os, sys",
    `_siren_dir = ${JSON.stringify(runtimeDir)}`,
    // First on the path, so an old siren-debug left in site-packages can't
    // shadow the extension's runtime.
    "if os.path.isdir(_siren_dir) and _siren_dir not in sys.path:",
    "    sys.path.insert(0, _siren_dir)",
    `os.environ.setdefault('SIREN_VSCODE_EVENTS', ${JSON.stringify(eventsFile)})`,
    "try:",
    "    import siren",
    "except Exception:",
    "    pass",
  ].join("\n");
  return `import sys; exec(${JSON.stringify(code)})\n`;
}

/** Install or remove the .pth that loads Siren in every process of a Python environment. */
export class EnvironmentInstaller implements vscode.Disposable {
  private readonly disposables: vscode.Disposable[] = [];

  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly runtime: Runtime,
  ) {
    this.disposables.push(
      vscode.commands.registerCommand("siren.enableEnvironment", () => this.enable()),
      vscode.commands.registerCommand("siren.disableEnvironment", () => this.disable()),
    );
    this.refreshInstalled();
  }

  private installed(): string[] {
    return this.context.globalState.get<string[]>(STATE_KEY, []);
  }

  /** Point every .pth this extension installed at the current runtime and workspace. */
  private refreshInstalled(): void {
    const still = this.installed().filter((file) => {
      if (!fs.existsSync(file)) {
        return false; // removed by hand, or the environment is gone
      }
      try {
        fs.writeFileSync(file, pthLine(this.runtime.stableRuntimeDir, this.runtime.eventsFile));
      } catch {
        // read-only now: leave it as it is
      }
      return true;
    });
    this.context.globalState.update(STATE_KEY, still);
  }

  async enable(): Promise<void> {
    const python = await resolvePython(vscode.window.activeTextEditor?.document.uri);
    try {
      const where = await locate(python);
      fs.mkdirSync(where.dir, { recursive: true });
      const file = path.join(where.dir, PTH_NAME);
      fs.writeFileSync(file, pthLine(this.runtime.stableRuntimeDir, this.runtime.eventsFile));
      await this.context.globalState.update(STATE_KEY, [...new Set([...this.installed(), file])]);
      const scope = where.venv ? "this virtual environment" : "this Python (for your user)";
      vscode.window.showInformationMessage(
        `Siren: enabled for ${scope}, Python ${where.version} at ${where.exe}. Every program it runs now has siren() without an import (terminals outside VS Code, servers, scripts run by other tools), and its values show in this editor. Programs already running need a restart.`,
      );
    } catch (error) {
      vscode.window.showErrorMessage(
        `Siren: couldn't enable it for ${python}: ${(error as Error).message}. Pick the project's interpreter with "Python: Select Interpreter" or set siren.pythonPath.`,
      );
    }
  }

  async disable(): Promise<void> {
    const python = await resolvePython(vscode.window.activeTextEditor?.document.uri);
    try {
      const where = await locate(python);
      const file = path.join(where.dir, PTH_NAME);
      const existed = fs.existsSync(file);
      fs.rmSync(file, { force: true });
      await this.context.globalState.update(
        STATE_KEY,
        this.installed().filter((f) => f !== file),
      );
      vscode.window.showInformationMessage(
        existed
          ? `Siren: disabled for Python ${where.version} at ${where.exe}. It's still available in VS Code terminals and the debugger.`
          : `Siren: it wasn't enabled for Python ${where.version} at ${where.exe}.`,
      );
    } catch (error) {
      vscode.window.showErrorMessage(`Siren: couldn't disable it for ${python}: ${(error as Error).message}`);
    }
  }

  dispose(): void {
    this.disposables.forEach((d) => d.dispose());
  }
}
