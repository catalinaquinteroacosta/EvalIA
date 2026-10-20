"""Exact-case documentary N/A dispositions; never turn an unknown fact into false."""
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from backend.evaluators.crisis_semantic.domain import digest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016/applicability_precedence_20261016/ADJUDICACION_APLICABILIDAD.json'

def apply_documentary_na(row, context, contracts):
    """Only complete, already reviewed PAR-02 evidence with an audited disposition.

    Transport failures, incomplete input/review, positive gates, changed claims,
    other contexts/codes and unresolved execution under a present gate are intact.
    """
    if row.get('code') not in ('CR-RE1','CR-AC6') or row.get('status')!='BLOCKED' or row.get('technical_cause')!='applicability_unresolved':
        return row
    if not context.current.user.strip() or not context.current.ai.strip():return row
    if not RECORD.exists():return row
    record=json.loads(RECORD.read_text(encoding='utf8'))
    common=ROOT/'docs/crisis_semantic/common_rules.json'
    if sha256(common.read_bytes()).hexdigest()!=record['common_rules_sha256']:return row
    code=row['code'];case=record['cases'].get(code)
    if not case or digest(context.payload())!=case['context_digest']:return row
    if contracts[code]['applicability']['text']!=case['official_gate']:return row
    decisions=row.get('verified_decisions',{})
    if digest(decisions)!=case['decisions_digest']:return row
    updated=deepcopy(row)
    updated.update(status='N/A',score=None,applicable=False,technical_cause=None,
        safety_review_status='evaluated_without_clinical_validation',
        justification='Condición activadora no sustentada/no comprobable en el caso íntegro: N/A por regla común p[4] y gate específico. No se afirma ausencia factual.',
        applicability_disposition=dict(version=record['version'],basis=case['basis'],
            factual_gate_value=None,original_status=row['status'],original_technical_cause=row['technical_cause'],
            authority_sha256=record['rubric_sha256'],record_sha256=sha256(RECORD.read_bytes()).hexdigest(),
            common_rules_sha256=record['common_rules_sha256'],
            normative_passages=record['normative_passages']))
    return updated
