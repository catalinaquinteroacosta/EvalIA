/** Step 2 only: literal contracts, not scoring or semantic extraction. */
import { children, paragraphText, paragraphRecord, paragraphs, descendants } from './docx_reader.mjs';

export const SCHEMA_VERSION = 'crisis-document-contract/1';
const familyHeading = /^(CR-\d{2}) · (.+)$/u;
const indicatorHeading = /^(CR-[A-Z]+\d+) · (.+)$/u;
const reference = record => ({ paragraph_id: record.id, start: 0, end: record.text.length });
const literal = records => ({ text: records.map(r => r.text).join('\n'), source_refs: records.map(reference) });

function descriptorRecords(cell, level, anomalies, code) {
  const selected = [];
  for (const node of children(cell)) {
    if (node.name === 'w:p') {
      const record = paragraphRecord(node);
      if (record.text.trim() !== '') selected.push(record);
    } else if (node.name === 'w:tbl') {
      for (const row of children(node, 'w:tr')) {
        const cells = children(row, 'w:tc');
        if (cells.length === 2 && paragraphs(cells[0]).map(r => r.text).join('') === level) {
          anomalies.push({ cause: 'nested_duplicate_level_marker', indicator: code, level,
            source_refs: paragraphs(cells[0]).map(reference), resolution: 'Preserved in source_paragraphs; excluded only from descriptor text.' });
          selected.push(...descriptorRecords(cells[1], level, anomalies, code));
        } else if (cells.length === 1) selected.push(...descriptorRecords(cells[0], level, anomalies, code));
        else throw new Error(`Unexpected nested descriptor table: ${code}/${level}`);
      }
    } else if (node.name !== 'w:tcPr') throw new Error(`Unexpected descriptor structure ${node.name}`);
  }
  return selected;
}

function parseIndicator(item, common, anomalies) {
  const { heading, blocks, family_code } = item;
  const match = indicatorHeading.exec(heading.text);
  const code = match[1], question = match[2];
  const table = blocks.filter(n => n.name === 'w:tbl');
  if (table.length !== 1) throw new Error(`Expected one outer table: ${code}`);
  const fields = {};
  for (const row of children(table[0], 'w:tr')) {
    const cells = children(row, 'w:tc');
    if (cells.length !== 2) throw new Error(`Expected two table columns: ${code}`);
    const label = paragraphs(cells[0]).map(r => r.text).join('');
    if (!['Aplicabilidad / N/A', '0', '1', '2', '3'].includes(label) || fields[label]) throw new Error(`Unknown/duplicate row ${code}: ${label}`);
    const records = descriptorRecords(cells[1], label, anomalies, code);
    if (!records.length) throw new Error(`Empty field ${code}: ${label}`);
    fields[label] = literal(records);
  }
  if (Object.keys(fields).length !== 5) throw new Error(`Incomplete levels/gate: ${code}`);
  const extras = blocks.filter(n => n.name === 'w:p').map(paragraphRecord).filter(r => r.text.trim() !== '');
  if (extras.some(r => !r.text.startsWith('Control de seguridad:'))) throw new Error(`Unclassified extra text: ${code}`);
  const source = [heading, ...blocks.flatMap(n => n.name === 'w:p' ? [paragraphRecord(n)] : paragraphs(n))];
  const gate = fields['Aplicabilidad / N/A'];
  const focuses = new Map();
  for (const level of ['0', '1', '2', '3']) {
    const field = fields[level];
    for (const ref of field.source_refs) {
      const record = source.find(r => r.id === ref.paragraph_id);
      const at = record.text.indexOf('Foco: ');
      if (at >= 0) {
        const text = record.text.slice(at + 6);
        const value = focuses.get(text) || { text, source_refs: [] };
        value.source_refs.push({ paragraph_id: record.id, start: at + 6, end: record.text.length });
        focuses.set(text, value);
      }
    }
  }
  const kind = gate.text.startsWith('General:') ? 'general' : gate.text.startsWith('Condicional.') ? 'conditional' : null;
  if (!kind) throw new Error(`Unknown gate kind: ${code}`);
  return { code, family_code, official_heading: literal([heading]),
    official_question: { text: question, source_refs: [{ paragraph_id: heading.id, start: code.length + 3, end: heading.text.length }] },
    construct: { representation: 'official_question_verbatim_no_separate_construct_label', text: question,
      source_refs: [{ paragraph_id: heading.id, start: code.length + 3, end: heading.text.length }] },
    focus: [...focuses.values()], applicability: { kind, ...gate },
    na_conditions: { representation: 'complete_applicability_passage_verbatim', ...gate },
    levels: Object.fromEntries(['0', '1', '2', '3'].map(level => [level, fields[level]])),
    exceptions: { representation: 'embedded_in_full_literal_passages_not_reinterpreted',
      coverage_refs: source.filter(r => r.text !== '').map(reference), common_rules_ref: 'common_rules.json' },
    safety_controls: extras.map(r => literal([r])),
    common_rules_ref: 'common_rules.json', source_paragraphs: source };
}

export function buildContracts(document) {
  const common = [], families = [], anomalies = [];
  let family = null, item = null;
  const flush = () => {
    if (item) { family.indicators.push(parseIndicator(item, common, anomalies)); item = null; }
  };
  for (const node of children(document.body)) {
    if (node.name === 'w:sectPr') continue;
    if (!['w:p', 'w:tbl'].includes(node.name)) throw new Error(`Unsupported body structure: ${node.name}`);
    const text = node.name === 'w:p' ? paragraphText(node) : '';
    const fm = familyHeading.exec(text), im = indicatorHeading.exec(text);
    if (fm) {
      flush();
      family = { schema_version: SCHEMA_VERSION, source_sha256: document.source_sha256,
        code: fm[1], title: fm[2], official_heading: literal([paragraphRecord(node)]),
        source_paragraphs: [paragraphRecord(node)], indicators: [] };
      families.push(family);
    } else if (im) {
      flush();
      if (!family) throw new Error('Indicator without family');
      item = { heading: paragraphRecord(node), blocks: [], family_code: family.code };
    } else if (item) item.blocks.push(node);
    else if (family) {
      if (node.name !== 'w:p') throw new Error('Unexpected family preamble table');
      const record = paragraphRecord(node); family.source_paragraphs.push(record);
      if (record.text.startsWith('Indicadores:')) family.official_declaration = literal([record]);
    } else common.push(...(node.name === 'w:p' ? [paragraphRecord(node)] : paragraphs(node)));
  }
  flush();
  for (const f of families) {
    const declared = Number(f.official_declaration?.text.match(/^Indicadores: (\d+)\./)?.[1]);
    if (declared !== f.indicators.length) throw new Error(`Family count mismatch: ${f.code}`);
    if (!f.title) throw new Error('Missing family title');
  }
  const codes = families.flatMap(f => f.indicators.map(i => i.code));
  if (new Set(codes).size !== codes.length) throw new Error('Duplicate indicator code');
  return { common: { schema_version: SCHEMA_VERSION, source_sha256: document.source_sha256,
    source_paragraphs: common, normative_passages: common.filter(r => r.text !== '').map(r => literal([r])) }, families, anomalies };
}

export function traceability(bundle) {
  const rows = [];
  const add = (family, indicator, field, value) => {
    for (const ref of value.source_refs || value.coverage_refs || []) {
      rows.push({ family, indicator, field, text: value.text ?? null, ...ref });
    }
  };
  bundle.common.normative_passages.forEach((v, n) => add(null, null, `common.${n}`, v));
  for (const f of bundle.families) {
    add(f.code, null, 'official_heading', f.official_heading);
    add(f.code, null, 'official_declaration', f.official_declaration);
    for (const i of f.indicators) {
      for (const name of ['official_heading', 'official_question', 'construct', 'applicability', 'na_conditions', 'exceptions']) add(f.code, i.code, name, i[name]);
      for (const [level, value] of Object.entries(i.levels)) add(f.code, i.code, `levels.${level}`, value);
      i.focus.forEach((v, n) => add(f.code, i.code, `focus.${n}`, v));
      i.safety_controls.forEach((v, n) => add(f.code, i.code, `safety_controls.${n}`, v));
    }
  }
  return rows;
}
