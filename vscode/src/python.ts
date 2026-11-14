import { execFile, spawn } from "node:child_process";
import * as vscode from "vscode";
import { Runtime } from "./runtime";

/**
 * The interpreter to run siren tools with: the `siren.pythonPath` setting,
 * else the one selected in the Python extension, else `python` on PATH.
 */
export async function resolvePython(resource?: vscode.Uri): Promise<string> {
  const configured = vscode.workspace.getConfiguration("siren").get<string>("pythonPath");
  if (configured) {
    return configured;
  }
  try {
    const ext = vscode.extensions.getExtension("ms-python.python");
    if (ext) {
      const api = ext.isActive ? ext.exports : await ext.activate();
      const envPath = api?.environments?.getActiveEnvironmentPath(resource);
      if (envPath) {
        const env = await api.environments.resolveEnvironment(envPath);
        const exe = env?.executable?.uri?.fsPath;
        if (exe) {
          return exe;
        }
      }
    }
  } catch {
    // fall through to PATH lookup
  }
  return process.platform === "win32" ? "python" : "python3";
}

export interface ToolResult {
  stdout: string;
  stderr: string;
}

/** Run `python -m <module> ...args` against the bundled runtime and capture output. */
export async function runModule(
  runtime: Runtime,
  module: string,
  args: string[],
  cwd?: string,
  resource?: vscode.Uri,
): Promise<ToolResult> {
  const python = await resolvePython(resource);
  return new Promise((resolve, reject) => {
    execFile(
      python,
      ["-m", module, ...args],
      { cwd, env: { ...process.env, ...runtime.env() }, maxBuffer: 16 * 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error) {
          const detail = (stderr || stdout || error.message).trim();
          reject(new Error(`${python} -m ${module} failed: ${detail}`));
        } else {
          resolve({ stdout, stderr });
        }
      },
    );
  });
}

/**
 * Call an op of siren/_bridge.py: the request goes to stdin as JSON and the
 * result comes back as JSON. An error raised in Python rejects the promise.
 */
export async function callBridge<T>(
  runtime: Runtime,
  op: string,
  args: Record<string, unknown> = {},
  resource?: vscode.Uri,
): Promise<T> {
  const python = await resolvePython(resource);
  return new Promise((resolve, reject) => {
    const child = spawn(python, ["-m", "siren._bridge"], {
      env: { ...process.env, ...runtime.env() },
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));
    child.on("error", (error) =>
      reject(new Error(`could not start Python (${python}): ${error.message}. Set siren.pythonPath.`)),
    );
    child.on("close", () => {
      let response: { ok: boolean; result?: T; error?: string };
      try {
        response = JSON.parse(stdout);
      } catch {
        reject(new Error((stderr || stdout || `${python} -m siren._bridge produced no output`).trim()));
        return;
      }
      if (response.ok) {
        resolve(response.result as T);
      } else {
        reject(new Error(response.error));
      }
    });
    child.stdin.end(JSON.stringify({ op, args }));
  });
}
