import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadBundle, OUTPUT, DEFAULT_SOURCE } from './generate_contracts.mjs';
import { readIndependentSource, validateIntegrity } from './integrity.mjs';
import { sha256, readDocx } from './docx_reader.mjs';

export async function validateStored(source = DEFAULT_SOURCE) {
  const { bundle, manifest, trace } = await loadBundle();
  const oracle = readIndependentSource(source);
  const result = validateIntegrity(bundle, oracle, trace, manifest);
  const doc = await readDocx(source);
  if (doc.document_xml_sha256 !== manifest.document_xml_sha256) result.discrepancies.push({ cause: 'source_identity', path: 'manifest.document_xml_sha256' });
  for (const artifact of manifest.generated_artifacts) {
    if (resolve(OUTPUT, artifact.file).startsWith(OUTPUT + '/') || resolve(OUTPUT, artifact.file).startsWith(OUTPUT + '\\')) {
      const actual = sha256(await readFile(resolve(OUTPUT, artifact.file)));
      if (actual !== artifact.sha256) result.discrepancies.push({ cause: 'artifact_hash', path: artifact.file });
    } else result.discrepancies.push({ cause: 'artifact_path', path: artifact.file });
  }
  result.status = result.discrepancies.length ? 'FAIL' : 'PASS';
  return result;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { const result = await validateStored(process.argv[2] || DEFAULT_SOURCE); console.log(JSON.stringify(result, null, 2)); if (result.status !== 'PASS') process.exitCode = 1; }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
