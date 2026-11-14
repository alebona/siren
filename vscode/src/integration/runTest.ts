// Launches a real VS Code (the minimum version the extension supports) with
// the extension loaded, a throwaway workspace and a throwaway home folder, so
// the suite never touches the developer's own snippets or settings.
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { runTests } from "@vscode/test-electron";

async function main(): Promise<void> {
  // When launched from a VS Code terminal or extension, these make the test
  // VS Code start as plain Node (ELECTRON_RUN_AS_NODE) and exit at once.
  for (const name of Object.keys(process.env)) {
    if (name === "ELECTRON_RUN_AS_NODE" || name.startsWith("VSCODE_")) {
      delete process.env[name];
    }
  }
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "siren-it-"));
  const workspace = path.join(root, "workspace");
  const home = path.join(root, "home");
  fs.mkdirSync(workspace);
  fs.mkdirSync(home);
  try {
    await runTests({
      version: "1.85.0",
      extensionDevelopmentPath: path.resolve(__dirname, "..", ".."),
      extensionTestsPath: path.resolve(__dirname, "suite"),
      launchArgs: [workspace, "--disable-extensions", "--user-data-dir", path.join(root, "user-data")],
      extensionTestsEnv: { HOME: home, USERPROFILE: home },
    });
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
