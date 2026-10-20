"""Lossless DOCX contracts. Regex is used only for document headings."""
from hashlib import sha256
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

EXPECTED = {'AF': 8, 'GD': 8, 'PS': 10, 'PA': 8, 'ND': 8,
            'CP': 8, 'IR': 8, 'EM': 13, 'CE': 10}
NAMESPACE = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def read_contracts(source):
    source = Path(source)
    raw = source.read_bytes()
    with ZipFile(source) as archive:
        document = ET.fromstring(archive.read('word/document.xml'))
    paragraphs = [''.join(t.text or '' for t in p.findall('.//w:t', NAMESPACE))
                  for p in document.findall('.//w:p', NAMESPACE)]
    headings = []
    for index, text in enumerate(paragraphs):
        match = re.match(r'^(AF|GD|PS|PA|ND|CP|IR|EM|CE)(\d+)\s', text)
        if match:
            headings.append((index, match.group(1) + match.group(2), match.group(1)))
    contracts = {}
    for position, (start, code, family) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(paragraphs)
        block = paragraphs[start:end]
        levels = {}
        for level in range(4):
            matches = [i for i, text in enumerate(block) if text == str(level)]
            if len(matches) != 1 or matches[0] + 1 >= len(block):
                raise ValueError(f'{code}: missing or duplicated descriptor {level}')
            levels[str(level)] = block[matches[0] + 1]
        gate = [text for text in block if text.startswith(('General:', 'Condicional:', 'Aplicabilidad:'))]
        if len(gate) != 1 or code in contracts:
            raise ValueError(f'{code}: gate missing/duplicated or duplicate indicator')
        contracts[code] = {'code': code, 'family': family, 'official_heading': block[0],
                           'applicability_literal': gate[0], 'levels': levels,
                           'paragraph_start_zero_based': start, 'paragraph_end_exclusive': end,
                           'paragraphs_literal': block}
    for family, count in EXPECTED.items():
        expected_codes = {f'{family}{i}' for i in range(1, count + 1)}
        if {code for code, c in contracts.items() if c['family'] == family} != expected_codes:
            raise ValueError(f'Incomplete official family {family}')
    return {'source_sha256': sha256(raw).hexdigest(), 'source_name': source.name,
            'preamble_literal': paragraphs[:headings[0][0]], 'contracts': contracts,
            'clinical_validation': False}
