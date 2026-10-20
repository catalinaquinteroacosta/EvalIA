/** Independent documentary comparison. No rubric interpretation or score decisions. */
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { isDeepStrictEqual } from 'node:util';

export function readIndependentSource(source) {
  const script = fileURLToPath(new URL('./independent_source.ps1', import.meta.url));
  const result = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', script, '-Source', source],
    { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024, windowsHide: true });
  if (result.error || result.status !== 0) throw new Error(`Independent source reader failed: ${result.error?.message || result.stderr}`);
  return JSON.parse(result.stdout.replace(/^\uFEFF/u, '').trim());
}

export function validateIntegrity(bundle, oracle, trace = null, manifest = null) {
  const discrepancies = [], counts = { indicators: 0, levels: 0, compared_fields: 0, resolved_references: 0 };
  const fail = (cause, path, expected, actual) => discrepancies.push({ cause, path, expected, actual });
  const equal = (actual, expected, path, cause = 'literal_content') => {
    counts.compared_fields++;
    if (!isDeepStrictEqual(actual, expected)) fail(cause, path, expected, actual);
  };
  const exactKeys = (obj, keys, path) => equal(Object.keys(obj || {}).sort(), [...keys].sort(), `${path}.keys`, 'schema');
  const source = new Map(oracle.paragraphs.map(p => [p.id, p.text]));
  const ref = (r, path) => {
    counts.resolved_references++;
    if (!source.has(r?.paragraph_id)) { fail('source_reference', path, 'existing paragraph', r); return ''; }
    const text = source.get(r.paragraph_id);
    if (!Number.isInteger(r.start) || !Number.isInteger(r.end) || r.start < 0 || r.end > text.length || r.end < r.start) {
      fail('source_reference', path, 'valid UTF-16 range', r); return '';
    }
    exactKeys(r, ['paragraph_id', 'start', 'end'], path);
    return text.slice(r.start, r.end);
  };
  const expectedRefs = records => records.map(r => ({ paragraph_id: r.id, start: 0, end: r.text.length }));
  const checkLiteral = (actual, expectedText, expectedReferences, path, extraKeys = []) => {
    exactKeys(actual, ['text', 'source_refs', ...extraKeys], path);
    equal(actual?.text, expectedText, `${path}.text`);
    equal(actual?.source_refs, expectedReferences, `${path}.source_refs`, 'source_reference');
    const reconstructed = (actual?.source_refs || []).map((r, n) => ref(r, `${path}.refs.${n}`)).join('\n');
    equal(actual?.text, reconstructed, `${path}.reconstructed`, 'source_reference');
  };
  equal(bundle.families.map(f => f.code), oracle.families.map(f => f.code), 'family_order', 'inventory');
  equal(bundle.common.source_sha256, oracle.source_sha256, 'common.source_sha256', 'source_identity');
  exactKeys(bundle.common, ['schema_version', 'source_sha256', 'source_paragraphs', 'normative_passages'], 'common');
  equal(bundle.common.schema_version, 'crisis-document-contract/1', 'common.schema_version', 'schema');
  const flattened = [...bundle.common.source_paragraphs];
  const firstFamily = oracle.families[0]?.heading.id;
  const commonEnd = oracle.paragraphs.findIndex(p => p.id === firstFamily);
  const expectedCommon = oracle.paragraphs.slice(0, commonEnd);
  equal(bundle.common.source_paragraphs, expectedCommon, 'common.source_paragraphs', 'coverage');
  equal(bundle.common.normative_passages.length, expectedCommon.filter(p => p.text !== '').length, 'common.passages.length', 'coverage');
  expectedCommon.filter(p => p.text !== '').forEach((r, n) => checkLiteral(bundle.common.normative_passages[n], r.text, expectedRefs([r]), `common.passages.${n}`));
  for (let fi = 0; fi < oracle.families.length; fi++) {
    const expectedFamily = oracle.families[fi], family = bundle.families[fi];
    if (!family) continue;
    const fp = expectedFamily.code;
    exactKeys(family, ['schema_version', 'source_sha256', 'code', 'title', 'official_heading', 'official_declaration', 'source_paragraphs', 'indicators'], fp);
    equal(family.schema_version, 'crisis-document-contract/1', `${fp}.schema_version`, 'schema');
    equal(family.source_sha256, oracle.source_sha256, `${fp}.source_sha256`, 'source_identity');
    equal(family.title, expectedFamily.title, `${fp}.title`);
    checkLiteral(family.official_heading, expectedFamily.heading.text, expectedRefs([expectedFamily.heading]), `${fp}.heading`);
    checkLiteral(family.official_declaration, expectedFamily.declaration.text, expectedRefs([expectedFamily.declaration]), `${fp}.declaration`);
    equal(family.indicators.map(i => i.code), expectedFamily.indicators.map(i => i.code), `${fp}.indicator_order`, 'inventory');
    const familyStart = oracle.paragraphs.findIndex(r => r.id === expectedFamily.heading.id);
    const familyEnd = oracle.paragraphs.findIndex(r => r.id === expectedFamily.indicators[0].heading.id);
    equal(family.source_paragraphs, oracle.paragraphs.slice(familyStart, familyEnd), `${fp}.source_paragraphs`, 'coverage');
    flattened.push(...family.source_paragraphs);
    for (let ii = 0; ii < expectedFamily.indicators.length; ii++) {
      const e = expectedFamily.indicators[ii], i = family.indicators[ii];
      if (!i) continue;
      counts.indicators++;
      const p = e.code;
      exactKeys(i, ['code', 'family_code', 'official_heading', 'official_question', 'construct', 'focus', 'applicability', 'na_conditions', 'levels', 'exceptions', 'safety_controls', 'common_rules_ref', 'source_paragraphs'], p);
      equal(i.family_code, expectedFamily.code, `${p}.family_code`, 'inventory');
      equal(i.common_rules_ref, 'common_rules.json', `${p}.common_rules_ref`, 'coverage');
      checkLiteral(i.official_heading, e.heading.text, expectedRefs([e.heading]), `${p}.heading`);
      const qr = [{ paragraph_id: e.heading.id, start: e.code.length + 3, end: e.heading.text.length }];
      checkLiteral(i.official_question, e.question, qr, `${p}.question`);
      checkLiteral(i.construct, e.question, qr, `${p}.construct`, ['representation']);
      equal(i.construct.representation, 'official_question_verbatim_no_separate_construct_label', `${p}.construct.representation`, 'schema');
      checkLiteral(i.applicability, e.gate.text, expectedRefs(e.gate.records), `${p}.applicability`, ['kind']);
      equal(i.applicability.kind, e.gate.text.startsWith('General:') ? 'general' : 'conditional', `${p}.kind`, 'applicability');
      checkLiteral(i.na_conditions, e.gate.text, expectedRefs(e.gate.records), `${p}.na_conditions`, ['representation']);
      equal(i.na_conditions.representation, 'complete_applicability_passage_verbatim', `${p}.na_representation`, 'schema');
      exactKeys(i.levels, ['0', '1', '2', '3'], `${p}.levels`);
      const focus = new Map();
      for (const level of ['0', '1', '2', '3']) {
        counts.levels++;
        checkLiteral(i.levels[level], e.levels[level].text, expectedRefs(e.levels[level].records), `${p}.levels.${level}`);
        for (const r of e.levels[level].records) {
          const pos = r.text.indexOf('Foco: ');
          if (pos !== -1) {
            const text = r.text.substring(pos + 6), value = focus.get(text) || { text, source_refs: [] };
            value.source_refs.push({ paragraph_id: r.id, start: pos + 6, end: r.text.length }); focus.set(text, value);
          }
        }
      }
      equal(i.focus, [...focus.values()], `${p}.focus`, 'focus');
      equal(i.safety_controls.length, e.safety.length, `${p}.safety.length`, 'safety');
      e.safety.forEach((r, n) => checkLiteral(i.safety_controls[n], r.text, expectedRefs([r]), `${p}.safety.${n}`));
      exactKeys(i.exceptions, ['representation', 'coverage_refs', 'common_rules_ref'], `${p}.exceptions`);
      equal(i.exceptions.representation, 'embedded_in_full_literal_passages_not_reinterpreted', `${p}.exceptions.representation`, 'schema');
      equal(i.exceptions.common_rules_ref, 'common_rules.json', `${p}.exceptions.common_rules_ref`, 'coverage');
      // Oracle boundaries are computed from original headings, not generated raw records.
      const at = oracle.paragraphs.findIndex(r => r.id === e.heading.id);
      const next = expectedFamily.indicators[ii + 1]?.heading.id || oracle.families[fi + 1]?.heading.id;
      const end = next ? oracle.paragraphs.findIndex(r => r.id === next) : oracle.paragraphs.length;
      const expectedRaw = oracle.paragraphs.slice(at, end);
      equal(i.source_paragraphs, expectedRaw, `${p}.source_paragraphs`, 'coverage');
      equal(i.exceptions.coverage_refs, expectedRefs(expectedRaw.filter(r => r.text !== '')), `${p}.exceptions.coverage_refs`, 'exceptions');
      flattened.push(...i.source_paragraphs);
    }
  }
  equal(flattened, oracle.paragraphs, 'complete_document_paragraph_sequence', 'coverage');
  equal(counts.indicators, 104, 'indicator_count', 'inventory');
  equal(bundle.families.length, 10, 'family_count', 'inventory');
  if (trace) {
    // Build the expected matrix independently from the authoritative fields above.
    const expected = [];
    const add = (family, indicator, field, text, refs) => refs.forEach(r => expected.push({ family, indicator, field, text, ...r }));
    expectedCommon.filter(r => r.text !== '').forEach((r, n) => add(null, null, `common.${n}`, r.text, expectedRefs([r])));
    oracle.families.forEach((f, fi) => {
      add(f.code, null, 'official_heading', f.heading.text, expectedRefs([f.heading]));
      add(f.code, null, 'official_declaration', f.declaration.text, expectedRefs([f.declaration]));
      f.indicators.forEach((e, ii) => {
        const qr = [{ paragraph_id: e.heading.id, start: e.code.length + 3, end: e.heading.text.length }];
        add(f.code, e.code, 'official_heading', e.heading.text, expectedRefs([e.heading]));
        add(f.code, e.code, 'official_question', e.question, qr);
        add(f.code, e.code, 'construct', e.question, qr);
        add(f.code, e.code, 'applicability', e.gate.text, expectedRefs(e.gate.records));
        add(f.code, e.code, 'na_conditions', e.gate.text, expectedRefs(e.gate.records));
        const at = oracle.paragraphs.findIndex(r => r.id === e.heading.id);
        const next = f.indicators[ii + 1]?.heading.id || oracle.families[fi + 1]?.heading.id;
        const raw = oracle.paragraphs.slice(at, next ? oracle.paragraphs.findIndex(r => r.id === next) : undefined);
        add(f.code, e.code, 'exceptions', null, expectedRefs(raw.filter(r => r.text !== '')));
        const focuses = new Map();
        for (const level of ['0', '1', '2', '3']) {
          add(f.code, e.code, `levels.${level}`, e.levels[level].text, expectedRefs(e.levels[level].records));
          for (const r of e.levels[level].records) {
            const at = r.text.indexOf('Foco: ');
            if (at >= 0) { const text = r.text.slice(at + 6), refs = focuses.get(text) || []; refs.push({ paragraph_id: r.id, start: at + 6, end: r.text.length }); focuses.set(text, refs); }
          }
        }
        [...focuses].forEach(([text, refs], n) => add(f.code, e.code, `focus.${n}`, text, refs));
        e.safety.forEach((r, n) => add(f.code, e.code, `safety_controls.${n}`, r.text, expectedRefs([r])));
      });
    });
    equal(trace, expected, 'traceability_matrix', 'traceability');
  }
  if (manifest) {
    exactKeys(manifest, ['schema_version', 'authority', 'source_path', 'source_sha256', 'document_xml_sha256', 'rubric_version', 'rubric_identifier', 'paragraph_count', 'table_count', 'family_count', 'indicator_count', 'general_count', 'conditional_count', 'families', 'normalization', 'generated_artifacts'], 'manifest');
    equal(manifest.schema_version, 'crisis-document-contract/1', 'manifest.schema_version', 'schema');
    equal(manifest.authority, 'original_docx_only', 'manifest.authority', 'schema');
    equal(manifest.rubric_version, null, 'manifest.rubric_version', 'source_identity');
    equal(manifest.rubric_identifier, `sha256:${oracle.source_sha256}`, 'manifest.rubric_identifier', 'source_identity');
    equal(manifest.source_sha256, oracle.source_sha256, 'manifest.source_sha256', 'source_identity');
    equal(manifest.paragraph_count, oracle.paragraph_count, 'manifest.paragraph_count', 'coverage');
    equal(manifest.table_count, oracle.table_count, 'manifest.table_count', 'coverage');
    equal(manifest.indicator_count, counts.indicators, 'manifest.indicator_count', 'inventory');
    equal(manifest.family_count, oracle.families.length, 'manifest.family_count', 'inventory');
    equal(manifest.general_count, oracle.families.flatMap(f => f.indicators).filter(i => i.gate.text.startsWith('General:')).length, 'manifest.general_count', 'inventory');
    equal(manifest.conditional_count, oracle.families.flatMap(f => f.indicators).filter(i => i.gate.text.startsWith('Condicional.')).length, 'manifest.conditional_count', 'inventory');
    equal(manifest.families, oracle.families.map(f => ({ code: f.code, title: f.title, count: f.indicators.length, file: `contracts_${f.code}.json` })), 'manifest.families', 'inventory');
  }
  return { status: discrepancies.length ? 'FAIL' : 'PASS', ...counts, source_sha256: oracle.source_sha256,
    paragraph_count: oracle.paragraph_count, table_count: oracle.table_count, discrepancies };
}
