import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { resolve, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readDocx, sha256 } from './docx_reader.mjs';
import { buildContracts, traceability } from './contracts.mjs';
import { readIndependentSource, validateIntegrity } from './integrity.mjs';

export const WORKSPACE = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
export const OUTPUT = resolve(WORKSPACE, 'docs/crisis_semantic');
export const DEFAULT_SOURCE = 'C:/Users/catal/OneDrive/Escritorio/PROYECTO DE GRADO/PUNTAJES EVALUADORES CRISIS.docx';
export const familyFile = code => `contracts_${code}.json`;

export async function loadBundle(directory = OUTPUT) {
  const json = async name => JSON.parse(await readFile(resolve(directory, name), 'utf8'));
  const manifest = await json('manifest.json');
  return { bundle: { common: await json('common_rules.json'), families: await Promise.all(manifest.families.map(f => json(f.file))) },
    manifest, trace: await json('traceability_matrix.json') };
}

export async function generate(source = DEFAULT_SOURCE) {
  const doc = await readDocx(source), bundle = buildContracts(doc), trace = traceability(bundle);
  const oracle = readIndependentSource(source);
  const indicators = bundle.families.flatMap(f => f.indicators);
  const artifacts = new Map();
  const json = (name, value) => artifacts.set(name, JSON.stringify(value, null, 2) + '\n');
  json('common_rules.json', bundle.common);
  bundle.families.forEach(f => json(familyFile(f.code), f));
  json('traceability_matrix.json', trace);
  const columns = ['family', 'indicator', 'field', 'paragraph_id', 'start', 'end', 'text'];
  const csv = v => `"${String(v ?? '').replaceAll('"', '""')}"`;
  artifacts.set('traceability_matrix.csv', [columns.map(csv).join(','), ...trace.map(r => columns.map(c => csv(r[c])).join(','))].join('\n') + '\n');
  json('document_structure_notes.json', { scope: 'structural extraction only; no rubric corrections',
    nested_tables: doc.table_count - indicators.length, duplicate_markers: bundle.anomalies,
    missing_separate_construct_labels: indicators.map(i => i.code),
    indicators_without_explicit_focus: indicators.filter(i => !i.focus.length).map(i => i.code),
    preservation: 'All original paragraphs, including empty paragraphs and nested markers, are retained exactly with OOXML paths.' });
  const manifest = { schema_version: 'crisis-document-contract/1', authority: 'original_docx_only',
    source_path: resolve(source), source_sha256: doc.source_sha256, document_xml_sha256: doc.document_xml_sha256,
    rubric_version: null, rubric_identifier: `sha256:${doc.source_sha256}`, paragraph_count: doc.paragraph_count,
    table_count: doc.table_count, family_count: bundle.families.length, indicator_count: indicators.length,
    general_count: indicators.filter(i => i.applicability.kind === 'general').length,
    conditional_count: indicators.filter(i => i.applicability.kind === 'conditional').length,
    families: bundle.families.map(f => ({ code: f.code, title: f.title, count: f.indicators.length, file: familyFile(f.code) })),
    normalization: 'OOXML paragraph boundaries represented as LF; text, punctuation and spaces are not corrected. Offsets use UTF-16 code units.',
    generated_artifacts: [] };
  const validation = validateIntegrity(bundle, oracle, trace, manifest);
  if (validation.status !== 'PASS') throw new Error(`Document integrity failed before writing: ${JSON.stringify(validation.discrepancies.slice(0, 6))}`);
  json('validation_report.json', { ...validation, validator: oracle.oracle,
    api_calls: 0, shared_cache_access: false, clinical_validation: false,
    status_scope: 'documentary_integrity_only', unresolved_documentary_discrepancies: 0 });
  artifacts.set('CONTRACTS.md', renderContracts(bundle));
  artifacts.set('README.md', renderReadme(manifest, validation));
  manifest.generated_artifacts = [...artifacts].map(([file, content]) => ({ file, sha256: sha256(content) }));
  json('manifest.json', manifest);
  await mkdir(OUTPUT, { recursive: true });
  // Generation is create-only. A second invocation cannot overwrite existing artifacts.
  for (const name of artifacts.keys()) {
    try { await stat(resolve(OUTPUT, name)); throw new Error(`Refusing to overwrite existing file: ${name}`); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  for (const [name, content] of artifacts) await writeFile(resolve(OUTPUT, name), content, { flag: 'wx', encoding: 'utf8' });
  return { ...validation, generated_files: [...artifacts.keys()], general: manifest.general_count, conditional: manifest.conditional_count };
}

function renderContracts(bundle) {
  const out = ['# Contratos oficiales de crisis', '', 'Transcripción documental. No contiene puntuadores ni decisiones clínicas nuevas.', '',
    'Constructo: se conserva la pregunta oficial porque el documento no presenta un campo separado con ese nombre. Las excepciones permanecen dentro de los pasajes íntegros; no se reinterpretan.', '',
    '## Reglas comunes', ''];
  out.push(...bundle.common.normative_passages.flatMap(p => [p.text, '']));
  for (const f of bundle.families) {
    out.push(`## ${f.official_heading.text}`, '', f.official_declaration.text, '');
    for (const i of f.indicators) {
      out.push(`### ${i.official_heading.text}`, '', '**Aplicabilidad y N/A**', '', i.applicability.text, '');
      for (const [level, value] of Object.entries(i.levels)) out.push(`**${level}**`, '', value.text, '');
      i.safety_controls.forEach(v => out.push(v.text, ''));
    }
  }
  return out.join('\n') + '\n';
}

function renderReadme(m, report) {
  return `# PASO 2 DE 9 Contratos documentales de crisis

Estado: integridad documental ${report.status}. No es validación clínica ni cierre de evaluadores.

Fuente: ${m.source_path}

SHA-256: ${m.source_sha256}

Inventario: ${m.indicator_count} indicadores; ${m.family_count} familias; ${m.general_count} generales; ${m.conditional_count} condicionales.

## Archivos

${m.families.map(f => `- [${f.code} ${f.title}](${f.file}): ${f.count} contratos completos.`).join('\n')}
- [Lectura completa de las diez familias](CONTRACTS.md)
- [Reglas comunes literales](common_rules.json)
- [Matriz de trazabilidad JSON](traceability_matrix.json) y [CSV](traceability_matrix.csv)
- [Validación independiente](validation_report.json)
- [Particularidades estructurales](document_structure_notes.json)
- [Decisiones documentales](documentary_decisions.md)
- [Ambigüedades pendientes](methodological_pending.md)
- [Resultados de pruebas](test_results.txt)
- [Informe de entrega](STEP_2_REPORT.md)

## Representación

Cada campo normativo contiene texto literal y referencias al XML original. Las referencias usan XPath y rangos UTF-16 desde cero; no son números de página. Los source_paragraphs conservan todos los párrafos, incluso vacíos y marcadores duplicados de tablas anidadas.

Constructo conserva la pregunta oficial sin inventar una etiqueta clínica. Foco se extrae únicamente cuando aparece Foco: en los descriptores. Ocho indicadores no contienen ese rótulo y conservan sus descriptores específicos completos. N/A conserva el pasaje íntegro de aplicabilidad. Excepciones remite al contenido íntegro del indicador y reglas comunes; no afirma que las excepciones implícitas hayan recibido adjudicación clínica.

Las decisiones de conversación están fuera de los contratos normativos. No hay lógica de puntuación, llamadas API, apertura de caché ni importaciones de evaluadores existentes.

## Reproducción

Desde la raíz del proyecto, con Node.js y Windows PowerShell disponibles:

\
node --test tests/crisis_semantic/contracts.test.mjs
node backend/evaluators/crisis_semantic/validate_contracts.mjs
\

El generador se ejecutó con node backend/evaluators/crisis_semantic/generate_contracts.mjs. Es create-only y rechazará sobrescribir estos archivos. La validación y las pruebas son de solo lectura salvo sus registros explícitos dentro de las carpetas autorizadas.

El oráculo independiente usa ZIP/.NET y XML DOM/XPath en PowerShell; el generador usa ZIP/zlib y un árbol XML en JavaScript. No comparten el lector ni el generador de contratos.
`;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { console.log(JSON.stringify(await generate(process.argv[2] || DEFAULT_SOURCE), null, 2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
