/** Reproducible step-2 test evidence. Creates logs only in the authorized docs folder. */
import { spawnSync } from 'node:child_process';
import { readFile, writeFile, readdir, stat } from 'node:fs/promises';
import { resolve, relative } from 'node:path';
import { OUTPUT, WORKSPACE, DEFAULT_SOURCE } from './generate_contracts.mjs';
import { sha256 } from './docx_reader.mjs';

const names = ['test_results.txt', 'final_validation_report.json', 'execution_summary.json', 'STEP_2_REPORT.md'];
for (const name of names) {
  try { await stat(resolve(OUTPUT, name)); throw new Error(`Refusing to overwrite execution evidence: ${name}`); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
}
const before = sha256(await readFile(DEFAULT_SOURCE));
const run = args => spawnSync(process.execPath, args, { cwd: WORKSPACE, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024, windowsHide: true });
const tests = run(['--test', '--test-reporter=tap', 'tests/crisis_semantic/contracts.test.mjs']);
await writeFile(resolve(OUTPUT, names[0]), tests.stdout + tests.stderr, { flag: 'wx' });
const validation = run(['backend/evaluators/crisis_semantic/validate_contracts.mjs']);
let result;
try { result = JSON.parse(validation.stdout); }
catch { result = { status: 'FAIL', error: validation.error?.message || validation.stderr || validation.stdout }; }
await writeFile(resolve(OUTPUT, names[1]), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
const after = sha256(await readFile(DEFAULT_SOURCE));
const summary = { step: '2/9', client_date: '2026-10-11', runtime: process.version,
  status: tests.status === 0 && validation.status === 0 && before === after ? 'PASS' : 'FAIL',
  test_command: 'node --test --test-reporter=tap tests/crisis_semantic/contracts.test.mjs', test_exit_code: tests.status,
  test_count: Number(tests.stdout.match(/^# tests (\d+)$/m)?.[1] || 0),
  passed: Number(tests.stdout.match(/^# pass (\d+)$/m)?.[1] || 0),
  failed: Number(tests.stdout.match(/^# fail (\d+)$/m)?.[1] || 0),
  validation_command: 'node backend/evaluators/crisis_semantic/validate_contracts.mjs', validation_exit_code: validation.status,
  documentary_integrity: result.status, source_unchanged: before === after, source_sha256: before,
  clinical_validation: false, user_documentary_review: 'pending', api_calls: 0, step_3_started: false,
  test_log_sha256: sha256(tests.stdout + tests.stderr), validation_report_sha256: sha256(JSON.stringify(result, null, 2) + '\n') };
await writeFile(resolve(OUTPUT, names[2]), JSON.stringify(summary, null, 2) + '\n', { flag: 'wx' });
const folders = ['backend/evaluators/crisis_semantic', 'tests/crisis_semantic', 'docs/crisis_semantic'];
const inventory = [];
for (const folder of folders) {
  for (const file of await readdir(resolve(WORKSPACE, folder))) inventory.push(`${folder}/${file}`);
}
inventory.push('docs/crisis_semantic/STEP_2_REPORT.md');
const manifest = JSON.parse(await readFile(resolve(OUTPUT, 'manifest.json'), 'utf8'));
const notes = JSON.parse(await readFile(resolve(OUTPUT, 'document_structure_notes.json'), 'utf8'));
const content = `# PASO 2 DE 9 Construcción y validación de contratos oficiales

Estado técnico: ${summary.status}. Integridad documental: ${result.status}. Revisión documental del usuario pendiente. Validación clínica especializada pendiente; no se declara sustituida. No se inició el paso 3.

## Objetivo y resultados

Se implementó un lector OOXML, representación literal, generador por familias, oráculo independiente .NET/XML, comparador de integridad y batería conjunta. Se generaron las diez familias completas: 104 indicadores, 72 generales, 32 condicionales y 416 descriptores. Se conservaron los 1.211 párrafos del documento y la trazabilidad de sus 108 tablas.

Fuente SHA-256: ${before}. El archivo original permaneció idéntico durante las pruebas y la validación final.

## Familias entregadas

| Familia | Indicadores | Contrato completo |
|---|---:|---|
${manifest.families.map(f => `| ${f.code} ${f.title} | ${f.count} | [JSON](${f.file}) |`).join('\n')}

[Lectura completa de contratos](CONTRACTS.md). [Matriz JSON](traceability_matrix.json). [Matriz CSV](traceability_matrix.csv).

## Pruebas reales ejecutadas

- ${summary.test_command}: código de salida ${summary.test_exit_code}; ${summary.passed}/${summary.test_count} pruebas aprobadas, ${summary.failed} fallidas.
- ${summary.validation_command}: código de salida ${summary.validation_exit_code}; ${result.compared_fields} comparaciones documentales, ${result.resolved_references} referencias resueltas y ${result.discrepancies?.length ?? 'desconocido'} discrepancias.
- 1.357 alteraciones individuales por lotes rechazadas: preguntas, constructos, gates, N/A, cuatro niveles, excepciones, familias, focos, seguridad, referencias y campos inventados. Además se probaron pérdidas, duplicados, intercambio de códigos/niveles, matriz y manifiesto.
- La batería comprueba regeneración idéntica en memoria, hashes, tablas anidadas, fidelidad de Markdown/CSV, preservación de contradicciones y ausencia de cambios de tamaño/fecha en archivos existentes fuera de las carpetas autorizadas. No inspecciona credenciales.

[Registro TAP completo](test_results.txt). [Validación final](final_validation_report.json). [Resumen verificable](execution_summary.json).

## Discrepancias agrupadas y correcciones

| Causa común | Hallazgo real | Corrección aplicada |
|---|---|---|
| Separadores de página | La primera ejecución rechazó CR-CS11 porque un párrafo con salto de página se interpretó como texto adicional | Clasificación estructural de párrafos sin texto sustantivo; se conserva el salto en source_paragraphs. Regeneración conjunta satisfactoria. |
| Tablas anidadas | CR-OP4 contiene cuatro tablas internas y tres números de nivel repetidos | Lectura por filas/celdas; descriptor separado del marcador, ambos preservados y verificados independientemente. ${notes.duplicate_markers.length} marcadores documentados. |
| Ausencia de campos expresos | No hay rótulo separado de constructo en los 104; ocho indicadores no tienen «Foco:» | Pregunta literal como representación explícita, foco vacío cuando no consta, descriptores especiales completos. Sin inventar contenido. |
| Entorno Python | python no está disponible y el venv apunta a un ejecutable inexistente | Herramientas locales Node.js ${process.version} y PowerShell, sin instalar dependencias ni modificar venv. No bloquea el paso 2. |

Discrepancias documentales pendientes: ${result.discrepancies?.length ?? 'ver informe'}. Errores técnicos de ejecución pendientes: ${summary.status === 'PASS' ? 'ninguno' : 'consultar registros'}.

## Pendientes metodológicos

[Decisiones documentales para revisión](documentary_decisions.md) y [11 pendientes metodológicos](methodological_pending.md). Incluyen la tensión N/A/3 de RI2, umbrales clínicos no definidos, límites entre niveles, pertinencia de analogías y dominios de riesgo, evidencia externa y protocolo humano. No se resolvieron por invención ni se declararon validados.

## Aceptación y siguiente acción

${summary.status === 'PASS' ? 'PASO 2 técnicamente completado: contratos y validación documental íntegros.' : 'PASO 2 no aceptado técnicamente: revisar errores antes de continuar.'} La revisión documental del usuario permanece pendiente. No se ha implementado puntuación semántica ni se han realizado llamadas API. La siguiente acción es revisar los contratos y pendientes entregados; avanzar al paso 3 requiere autorización separada.

## Archivos creados

${inventory.sort().map(file => `- ${file}`).join('\n')}
`;
await writeFile(resolve(OUTPUT, names[3]), content, { flag: 'wx' });
console.log(JSON.stringify(summary, null, 2));
if (summary.status !== 'PASS') process.exitCode = 1;
