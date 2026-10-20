import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { resolve, relative } from 'node:path';
import { readDocx, parseXml, descendants, paragraphText, sha256 } from '../../backend/evaluators/crisis_semantic/docx_reader.mjs';
import { buildContracts, traceability } from '../../backend/evaluators/crisis_semantic/contracts.mjs';
import { loadBundle, WORKSPACE, DEFAULT_SOURCE, OUTPUT } from '../../backend/evaluators/crisis_semantic/generate_contracts.mjs';
import { readIndependentSource, validateIntegrity } from '../../backend/evaluators/crisis_semantic/integrity.mjs';
import { validateStored } from '../../backend/evaluators/crisis_semantic/validate_contracts.mjs';

let bundle, oracle, trace, manifest, baseline, document;
const authorized = ['backend/evaluators/crisis_semantic', 'tests/crisis_semantic', 'docs/crisis_semantic'];
async function protectedSnapshot(directory = WORKSPACE) {
  const result = {};
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name), rel = relative(WORKSPACE, path).replaceAll('\\', '/');
    // Never inspect credentials, dependency installs or git internals.
    if (authorized.some(a => rel === a || rel.startsWith(a + '/')) || entry.name.startsWith('.') || ['venv', 'node_modules'].includes(entry.name)) continue;
    if (entry.isDirectory()) Object.assign(result, await protectedSnapshot(path));
    else if (entry.isFile()) { const s = await stat(path); result[rel] = [s.size, s.mtimeMs]; }
  }
  return result;
}
before(async () => {
  baseline = await protectedSnapshot();
  ({ bundle, trace, manifest } = await loadBundle());
  oracle = readIndependentSource(DEFAULT_SOURCE);
  document = await readDocx(DEFAULT_SOURCE);
});
after(async () => {
  assert.deepEqual(await protectedSnapshot(), baseline, 'Tests must not mutate existing files outside authorized folders');
  console.log(`Protected existing files unchanged: ${Object.keys(baseline).length} (size/mtime guard; credentials excluded)`);
});

const all = value => value.families.flatMap(f => f.indicators);
const check = (value, matrix = null, identity = null) => validateIntegrity(value, oracle, matrix, identity);
function mutationBatch(label, mutate, filter = () => true) {
  test(label, () => {
    let count = 0;
    for (let f = 0; f < bundle.families.length; f++) {
      for (let n = 0; n < bundle.families[f].indicators.length; n++) {
        if (!filter(bundle.families[f].indicators[n])) continue;
        const changed = structuredClone(bundle);
        mutate(changed.families[f].indicators[n]);
        assert.equal(check(changed).status, 'FAIL', `Undetected mutation: ${label}/${changed.families[f].indicators[n].code}`);
        count++;
      }
    }
    assert.ok(count > 0); console.log(`${label}: ${count} altered contracts rejected`);
  });
}

test('All 104 contracts match original through independent ZIP/.NET XML reader', () => {
  const result = check(bundle, trace, manifest);
  assert.equal(result.status, 'PASS', JSON.stringify(result.discrepancies));
  assert.equal(result.indicators, 104); assert.equal(result.levels, 416);
  assert.equal(result.paragraph_count, 1211); assert.equal(result.table_count, 108);
  assert.deepEqual(bundle.families.map(f => f.indicators.length), [11, 10, 10, 10, 10, 10, 10, 10, 13, 10]);
  assert.equal(all(bundle).filter(i => i.applicability.kind === 'conditional').length, 32);
  assert.equal(all(bundle).filter(i => i.applicability.kind === 'general').length, 72);
});
test('Fresh in-memory generation matches every stored family and matrix', () => {
  const rebuilt = buildContracts(document);
  assert.deepEqual(rebuilt.families, bundle.families); assert.deepEqual(rebuilt.common, bundle.common);
  assert.deepEqual(traceability(rebuilt), trace);
  assert.equal(check(rebuilt, traceability(rebuilt), manifest).status, 'PASS');
});
test('Stored artifacts and original XML identity have valid SHA-256 hashes', async () => {
  const result = await validateStored();
  assert.equal(result.status, 'PASS', JSON.stringify(result.discrepancies));
  assert.equal(sha256(await readFile(DEFAULT_SOURCE)), manifest.source_sha256);
});
test('Nested CR-OP4 tables preserve four descriptors and three duplicate markers', () => {
  const i = all(bundle).find(i => i.code === 'CR-OP4');
  for (const level of ['0', '1', '2', '3']) assert.ok(!/^\d(?:\n|$)/u.test(i.levels[level].text));
  assert.ok(i.levels['1'].text.includes('probable'));
  assert.ok(i.levels['2'].text.includes('posibilidad'));
  assert.equal(i.source_paragraphs.filter(p => ['1', '2', '3'].includes(p.text)).length, 6);
  assert.equal(buildContracts(document).anomalies.length, 3);
});
test('All eight indicators without an explicit Foco retain empty focus and full special anchors', () => {
  assert.deepEqual(all(bundle).filter(i => i.focus.length === 0).map(i => i.code),
    ['CR-OP4', 'CR-RI2', 'CR-RI3', 'CR-RI6', 'CR-RI9', 'CR-RI10', 'CR-RI12', 'CR-RI13']);
});
test('Common contradictions remain verbatim; no conversation decision rewrites the rubric', () => {
  const common = bundle.common.normative_passages.map(p => p.text).join('\n');
  assert.ok(common.includes('no obliga a indagarlo para obtener 3 en CR-RI2'));
  assert.ok(common.includes('Marcar N/A únicamente si el gate condicional no se activa'));
  assert.ok(all(bundle).find(i => i.code === 'CR-CE10').applicability.text.includes('al menos dos turnos previos'));
  assert.ok(all(bundle).find(i => i.code === 'CR-RI9').applicability.text.includes('o el caso requiere localizarlos'));
});
test('Reader preserves runs, entities, tabs, line breaks, spaces and UTF-16 offsets', () => {
  const tree = parseXml('<w:p><w:r><w:t xml:space="preserve"> A&amp;B </w:t></w:r><w:r><w:t>&#x1F642;&lt;</w:t><w:tab/><w:br/><w:t>fin</w:t></w:r></w:p>');
  assert.equal(paragraphText(descendants(tree, 'w:p')[0]), ' A&B 🙂<\t\nfin');
  assert.throws(() => parseXml('<w:p><w:t></w:p>'), /Unbalanced/);
  assert.throws(() => parseXml('<!DOCTYPE x><w:p/>'), /DTD/);
});
mutationBatch('Altered official questions', i => { i.official_question.text += ' ALTERED'; });
mutationBatch('Altered construct representations', i => { i.construct.text = 'Invented construct'; });
mutationBatch('Altered applicability gates', i => { i.applicability.text += ' ALTERED'; });
mutationBatch('Altered N/A conditions', i => { i.na_conditions.text += ' ALTERED'; });
for (const level of ['0', '1', '2', '3']) mutationBatch(`Altered level ${level} descriptors`, i => { i.levels[level].text += ' ALTERED'; });
mutationBatch('Omitted exception coverage', i => { i.exceptions.coverage_refs.pop(); });
mutationBatch('Wrong indicator family', i => { i.family_code = 'CR-99'; });
mutationBatch('Altered explicit focus', i => { i.focus[0].text += ' ALTERED'; }, i => i.focus.length > 0);
mutationBatch('Omitted safety controls', i => { i.safety_controls.pop(); }, i => i.safety_controls.length > 0);
mutationBatch('Wrong paragraph source references', i => { i.official_question.source_refs[0].paragraph_id = '/invalid'; });
mutationBatch('Invented normative fields', i => { i.invented_exception = 'New clinical threshold'; });
test('Loss, duplicates, swapped codes and swapped levels are detected despite matching total count', () => {
  const mutations = [
    b => { b.families[0].indicators.pop(); },
    b => { b.families[0].indicators[1] = structuredClone(b.families[0].indicators[0]); },
    b => { const a = b.families[0].indicators; [a[0].code, a[1].code] = [a[1].code, a[0].code]; },
    b => { const l = b.families[8].indicators[1].levels; [l['1'], l['3']] = [l['3'], l['1']]; },
    b => { b.common.normative_passages[2].text += ' altered'; },
    b => { b.common.source_paragraphs.pop(); },
    b => { b.families[0].source_sha256 = '0'.repeat(64); },
  ];
  for (const mutate of mutations) { const changed = structuredClone(bundle); mutate(changed); assert.equal(check(changed).status, 'FAIL'); }
});
test('Traceability deletion, alteration and unresolvable offsets are rejected', () => {
  const changed = structuredClone(trace); changed[0].text += ' altered';
  assert.equal(check(bundle, changed).status, 'FAIL');
  assert.equal(check(bundle, trace.slice(1)).status, 'FAIL');
  const bad = structuredClone(bundle); bad.families[0].indicators[0].official_question.source_refs[0].end = 999999;
  assert.equal(check(bad).status, 'FAIL');
});
test('CSV matrix decodes exactly to the independently validated JSON matrix', async () => {
  const csv = await readFile(resolve(OUTPUT, 'traceability_matrix.csv'), 'utf8');
  const rows = []; let row = [], cell = '', quoted = false;
  for (let n = 0; n < csv.length; n++) {
    const char = csv[n];
    if (char === '"') {
      if (quoted && csv[n + 1] === '"') { cell += '"'; n++; } else quoted = !quoted;
    } else if (char === ',' && !quoted) { row.push(cell); cell = ''; }
    else if (char === '\n' && !quoted) { row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += char;
  }
  assert.equal(quoted, false); assert.equal(cell, '');
  assert.deepEqual(rows[0], ['family', 'indicator', 'field', 'paragraph_id', 'start', 'end', 'text']);
  assert.deepEqual(rows.slice(1), trace.map(r => rows[0].map(key => String(r[key] ?? ''))));
});
test('Human-readable ten-family document includes every original question, gate, descriptor and safety passage', async () => {
  const markdown = await readFile(resolve(OUTPUT, 'CONTRACTS.md'), 'utf8');
  for (const f of oracle.families) {
    assert.ok(markdown.includes(f.heading.text)); assert.ok(markdown.includes(f.declaration.text));
    for (const i of f.indicators) {
      assert.ok(markdown.includes(i.heading.text), i.code); assert.ok(markdown.includes(i.gate.text), i.code);
      for (const level of ['0', '1', '2', '3']) assert.ok(markdown.includes(i.levels[level].text), `${i.code}/${level}`);
      for (const safety of i.safety) assert.ok(markdown.includes(safety.text), i.code);
    }
  }
  for (const p of bundle.common.normative_passages) assert.ok(markdown.includes(p.text));
});
test('Manifest inventory, source identity and fabricated official versions are rejected', () => {
  for (const mutate of [m => m.general_count++, m => m.source_sha256 = 'bad', m => m.rubric_version = 'invented', m => m.families.reverse()]) {
    const changed = structuredClone(manifest); mutate(changed);
    assert.equal(check(bundle, trace, changed).status, 'FAIL');
  }
});
test('Code modules import only builtins and local documentary modules, with no network/cache/legacy imports', async () => {
  const folder = resolve(WORKSPACE, 'backend/evaluators/crisis_semantic');
  for (const file of await readdir(folder)) {
    if (!file.endsWith('.mjs')) continue;
    const text = await readFile(resolve(folder, file), 'utf8');
    const imports = [...text.matchAll(/from\s+['"]([^'"]+)['"]/g)].map(m => m[1]);
    assert.ok(imports.every(name => name.startsWith('node:') || name.startsWith('./')), file);
    assert.ok(!/fetch\s*\(|https?\.request|semantic_cache|evaluation_runner|\.env\b|OpenAI\s*\(/.test(text), file);
  }
});
