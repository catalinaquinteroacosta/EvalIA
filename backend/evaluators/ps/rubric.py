"""PS rubric context. Do not use regex legacy scores as an oracle."""
import json
from pathlib import Path
from .scoring import CODES

DATA = json.loads(Path(__file__).with_name('rubric_reference.json').read_text(encoding='utf-8'))

def rubric_for(code: str) -> dict:
    if code not in CODES: raise ValueError('Unknown PS indicator')
    indicator = next(i for i in DATA['criterion']['indicators'] if i['code'] == code)
    applicability, requirement = DATA['official_ps_summary'][code]
    return {'code':code, 'question':indicator['question'], 'reference_levels':DATA['official_full_anchors'][code]['levels'], 'applicability':DATA['official_full_anchors'][code]['applicability'], 'requirement':requirement}
