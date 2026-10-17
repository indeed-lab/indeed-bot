/** Bundle a self-contained browser module and preserve dependency licenses. */
import { build } from "esbuild";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const output = join(root, "web", "dist");
await mkdir(output, { recursive: true });

await build({
  absWorkingDir: root,
  entryPoints: ["web/engine.js"],
  outfile: "web/dist/engine.js",
  bundle: true,
  format: "esm",
  platform: "browser",
  target: "es2022",
  minify: true,
  sourcemap: false,
  legalComments: "none",
  banner: { js: "/* Indeed Lab · MIT. Dependency licenses: ./THIRD_PARTY_NOTICES.txt */" },
});

const notices = [
  "Indeed Bot browser runtime — third-party notices",
  "This file must accompany redistributed engine.js bundles.",
  "\nIndeed Lab / indeed-bot\n" + await readFile(join(root, "LICENSE"), "utf8"),
];
for (const name of ["franc-min", "trigram-utils", "n-gram", "collapse-white-space"]) {
  const directory = join(root, "node_modules", name);
  const metadata = JSON.parse(await readFile(join(directory, "package.json"), "utf8"));
  // franc-min's npm archive omits its monorepo license; a versioned upstream
  // copy is retained in the source tree so building never needs the network.
  const path = name === "franc-min"
    ? join(root, "web", "licenses", "franc-min.txt")
    : join(directory, "license");
  notices.push(`\n${name} ${metadata.version}\n${await readFile(path, "utf8")}`);
}
await writeFile(join(output, "THIRD_PARTY_NOTICES.txt"), notices.join("\n"));
const bytes = (await readFile(join(output, "engine.js"))).length;
console.log(`Built web/dist/engine.js (${(bytes / 1024).toFixed(1)} KiB) and THIRD_PARTY_NOTICES.txt.`);
