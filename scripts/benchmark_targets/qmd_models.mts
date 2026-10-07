// Fetch native model assets once; corpus indexes stay isolated per job.
import { createHash } from "node:crypto";
import { createReadStream, writeFileSync } from "node:fs";

const { pullModels, resolveModels } = await import("/opt/qmd/src/llm.ts");
const models = resolveModels();
const assets: Record<string, unknown> = {};
for (const [role, uri] of Object.entries(models)) {
  const [asset] = await pullModels([uri]);
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(asset.path)) hash.update(chunk);
  assets[role] = { ...asset, sha256: hash.digest("hex") };
}
writeFileSync("/opt/qmd-models.json", JSON.stringify(assets, null, 2) + "\n");
