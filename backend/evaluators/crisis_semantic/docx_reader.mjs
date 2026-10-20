/** Read-only OOXML reader. No Python, dependencies, network or evaluator imports. */
import { readFile } from 'node:fs/promises';
import { inflateRawSync } from 'node:zlib';
import { createHash } from 'node:crypto';

export const sha256 = value => createHash('sha256').update(value).digest('hex');

export function readZipEntry(buffer, wanted) {
  let eocd = -1;
  for (let p = buffer.length - 22; p >= Math.max(0, buffer.length - 65557); p--) {
    if (buffer.readUInt32LE(p) === 0x06054b50) { eocd = p; break; }
  }
  if (eocd < 0) throw new Error('Missing ZIP directory');
  const count = buffer.readUInt16LE(eocd + 10);
  let p = buffer.readUInt32LE(eocd + 16);
  for (let i = 0; i < count; i++) {
    if (buffer.readUInt32LE(p) !== 0x02014b50) throw new Error('Invalid ZIP directory');
    const flags = buffer.readUInt16LE(p + 8), method = buffer.readUInt16LE(p + 10);
    const size = buffer.readUInt32LE(p + 20), length = buffer.readUInt16LE(p + 28);
    const extra = buffer.readUInt16LE(p + 30), comment = buffer.readUInt16LE(p + 32);
    const name = buffer.subarray(p + 46, p + 46 + length).toString('utf8');
    if (name === wanted) {
      if (flags & 1) throw new Error('Encrypted DOCX is unsupported');
      const offset = buffer.readUInt32LE(p + 42);
      if (buffer.readUInt32LE(offset) !== 0x04034b50) throw new Error('Invalid local ZIP entry');
      const start = offset + 30 + buffer.readUInt16LE(offset + 26) + buffer.readUInt16LE(offset + 28);
      const compressed = buffer.subarray(start, start + size);
      const data = method === 0 ? compressed : method === 8 ? inflateRawSync(compressed) : null;
      if (!data) throw new Error(`Unsupported ZIP method ${method}`);
      if (data.length !== buffer.readUInt32LE(p + 24)) throw new Error('ZIP size mismatch');
      return data;
    }
    p += 46 + length + extra + comment;
  }
  throw new Error(`Missing ZIP entry ${wanted}`);
}

function decode(text) {
  return text.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (_, code) => {
    if (code.startsWith('#x')) return String.fromCodePoint(parseInt(code.slice(2), 16));
    if (code.startsWith('#')) return String.fromCodePoint(Number(code.slice(1)));
    return { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" }[code];
  });
}

/** Tokenization is structural XML processing, never semantic evaluation. */
export function parseXml(xml) {
  if (/<!DOCTYPE|<!ENTITY/i.test(xml)) throw new Error('DTD/entities are unsupported');
  const root = { name: '#document', children: [], counts: {}, path: '' };
  const stack = [root];
  const tokens = xml.match(/<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<[^>]+>|[^<]+/g) || [];
  for (const token of tokens) {
    if (token.startsWith('<?') || token.startsWith('<!--')) continue;
    const parent = stack.at(-1);
    if (!token.startsWith('<')) { parent.children.push(decode(token)); continue; }
    if (token.startsWith('</')) {
      if (stack.length === 1 || stack.at(-1).name !== token.slice(2, -1).trim()) throw new Error('Unbalanced XML');
      stack.pop(); continue;
    }
    const name = token.match(/^<([^\s/>]+)/)?.[1];
    if (!name) throw new Error('Unsupported XML token');
    const ordinal = parent.counts[name] = (parent.counts[name] || 0) + 1;
    const node = { name, path: `${parent.path}/${name}[${ordinal}]`, children: [], counts: {} };
    parent.children.push(node);
    if (!token.endsWith('/>')) stack.push(node);
  }
  if (stack.length !== 1) throw new Error('Unclosed XML');
  return root;
}

export const children = (node, name) => node.children.filter(c => typeof c !== 'string' && (!name || c.name === name));
export function descendants(node, name) {
  return children(node).flatMap(c => [...(c.name === name ? [c] : []), ...descendants(c, name)]);
}
export function paragraphText(node) {
  const visit = n => {
    if (typeof n === 'string') return '';
    if (n.name === 'w:t') return n.children.filter(c => typeof c === 'string').join('');
    if (n.name === 'w:tab') return '\t';
    if (n.name === 'w:br' || n.name === 'w:cr') return '\n';
    return n.children.map(visit).join('');
  };
  return visit(node);
}
export const paragraphRecord = node => ({ id: node.path, text: paragraphText(node) });
export const paragraphs = node => descendants(node, 'w:p').map(paragraphRecord);

export async function readDocx(path) {
  const buffer = await readFile(path), xmlBuffer = readZipEntry(buffer, 'word/document.xml');
  const tree = parseXml(xmlBuffer.toString('utf8'));
  const body = descendants(tree, 'w:body')[0];
  if (!body) throw new Error('Missing OOXML body');
  for (const tag of ['w:ins', 'w:del', 'w:altChunk', 'w:txbxContent', 'w:sym', 'w:footnoteReference', 'w:endnoteReference', 'w:vanish']) {
    if (descendants(body, tag).length) throw new Error(`Manual source review required: ${tag}`);
  }
  return { body, source_sha256: sha256(buffer), document_xml_sha256: sha256(xmlBuffer),
    paragraph_count: descendants(body, 'w:p').length, table_count: descendants(body, 'w:tbl').length };
}
