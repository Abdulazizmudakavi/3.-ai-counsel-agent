// Generates TypeScript types from the backend's JSON Schemas (../contracts), so the console
// and the API share one definition of each record. Run after re-exporting the schemas.
import { compileFromFile } from "json-schema-to-typescript";
import { readdirSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "..", "contracts");
const out = join(here, "..", "lib", "contracts");
mkdirSync(out, { recursive: true });

for (const file of readdirSync(src).filter((f) => f.endsWith(".schema.json"))) {
  const ts = await compileFromFile(join(src, file), {
    bannerComment: `/* Generated from contracts/${file} by scripts/gen-types.mjs. Do not edit. */`,
    additionalProperties: false,
    style: { singleQuote: false },
  });
  const name = file.replace(".schema.json", ".ts");
  writeFileSync(join(out, name), ts);
  console.log(`wrote lib/contracts/${name}`);
}
