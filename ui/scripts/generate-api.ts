#!/usr/bin/env npx tsx
/**
 * Generate TypeScript types from the OpenAPI spec.
 *
 * Usage: npx tsx scripts/generate-api.ts
 *
 * Outputs to lib/api/schema.d.ts. Commit the generated output —
 * CI regenerates and diffs to catch drift.
 */
import { execSync } from "child_process";
import path from "path";

const specPath = path.resolve(__dirname, "../../docs/contracts/api.openapi.yaml");
const outPath = path.resolve(__dirname, "../lib/api/schema.d.ts");

execSync(
  `npx openapi-typescript "${specPath}" -o "${outPath}"`,
  { stdio: "inherit" }
);

console.log(`Generated ${outPath}`);
