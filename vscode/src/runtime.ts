import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";

export const EVENTS_ENV = "SIREN_VSCODE_EVENTS";

/**
 * Owns the bundled Python runtime and makes it visible to Python processes
 * started from VS Code: integrated terminals (via the environment variable
 * collection) and Python debug sessions (via a debug configuration provider).
 */
export class Runtime implements vscode.Disposable {
  readonly runtimeDir: string;
  readonly eventsFile: string;
  private readonly disposables: vscode.Disposable[] = [];

  constructor(private readonly context: vscode.ExtensionContext) {
    this.runtimeDir = context.asAbsolutePath("python");
    const storage = (context.storageUri ?? context.globalStorageUri).fsPath;
    fs.mkdirSync(storage, { recursive: true });
    this.eventsFile = path.join(storage, "events.jsonl");
    fs.writeFileSync(this.eventsFile, "");

    this.applyTerminalEnv();
    this.disposables.push(
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("siren.injectRuntime")) {
          this.applyTerminalEnv();
        }
      }),
    );

    const provider: vscode.DebugConfigurationProvider = {
      resolveDebugConfiguration: (_folder, config) => {
        if (enabled()) {
          config.env = { ...(config.env ?? {}), ...this.env(config.env?.PYTHONPATH) };
        }
        return config;
      },
    };
    for (const type of ["debugpy", "python"]) {
      this.disposables.push(vscode.debug.registerDebugConfigurationProvider(type, provider));
    }
  }

  /** Environment that makes the runtime importable, merged with an existing PYTHONPATH. */
  env(existingPythonPath = process.env.PYTHONPATH): Record<string, string> {
    return {
      PYTHONPATH: [this.runtimeDir, existingPythonPath].filter(Boolean).join(path.delimiter),
      [EVENTS_ENV]: this.eventsFile,
      PYTHONIOENCODING: "utf-8",
    };
  }

  private applyTerminalEnv(): void {
    const collection = this.context.environmentVariableCollection;
    collection.clear();
    if (!enabled()) {
      return;
    }
    collection.description = "Makes `siren` available to Python programs run in this terminal.";
    // A trailing separator would add the current directory to sys.path, so
    // only prepend when there is something to prepend to.
    if (process.env.PYTHONPATH) {
      collection.prepend("PYTHONPATH", this.runtimeDir + path.delimiter);
    } else {
      collection.replace("PYTHONPATH", this.runtimeDir);
    }
    collection.replace(EVENTS_ENV, this.eventsFile);
  }

  dispose(): void {
    this.disposables.forEach((d) => d.dispose());
  }
}

function enabled(): boolean {
  return vscode.workspace.getConfiguration("siren").get<boolean>("injectRuntime", true);
}
