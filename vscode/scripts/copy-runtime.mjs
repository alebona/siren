// Copies the Python runtime (../siren/*.py) into python/siren so it ships
// inside the extension. The repo's siren/ folder stays the single source.
import { copyFileSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const src = join(root, "..", "siren");
const dest = join(root, "python", "siren");

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });

const files = readdirSync(src).filter((name) => name.endsWith(".py"));
for (const name of files) {
  copyFileSync(join(src, name), join(dest, name));
}
console.log(`copied ${files.length} runtime files to python/siren`);
