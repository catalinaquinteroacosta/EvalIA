"""Lossless export views of persisted results. No scoring or semantic calls."""
import json


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def indicator_records(payload):
    """Prefer native persisted rows; retain legacy rows when native is absent."""
    rows = []
    for turn in payload.get('results') or []:
        evaluation = turn.get('evaluation') or {}
        public = evaluation.get('result') or {}
        audit = public.get('validated_audit') or {}
        native = audit.get('indicator_results') or public.get('indicator_results')
        indicators = native if native is not None else evaluation.get('indicators') or public.get('indicator_details') or []
        for indicator in indicators:
            code = indicator.get('code') or indicator.get('indicator_code')
            status = indicator.get('status')
            if not status:
                status = 'N/A' if indicator.get('applicable') is False else 'SCORED' if indicator.get('score') is not None else 'BLOCKED'
            score = indicator.get('score') if status == 'SCORED' else None
            applicable = (True if status == 'SCORED' else False if status == 'N/A'
                          else indicator.get('applicable'))
            if applicable is None:
                applicable = {'APPLICABLE': True, 'NOT_APPLICABLE': False}.get(indicator.get('applicability'))
            rows.append(dict(response_id=turn.get('response_id'), turn=turn.get('turn_number'),
                model=(turn.get('model') or {}).get('name'), code=code, status=status, score=score,
                applicable=applicable, reader_model=audit.get('reader_model'),
                engine=public.get('engine_version') or audit.get('engine'),
                evaluation_id=evaluation.get('evaluation_id'), review_id=evaluation.get('review_id'),
                indicator=indicator, audit=audit))
    return rows


def append_xlsx_audit(workbook, payload):
    """Append audit sheets; JSON is chunked so Excel never silently truncates it."""
    sheet = workbook.create_sheet('Indicadores por turno')
    sheet.append(['Respuesta ID','Turno','Modelo evaluado','Indicador','Estado','Puntaje 0-3','Aplicable',
                  'Modelo lector','Motor/version','Evaluacion ID','Revision ID'])
    detail = workbook.create_sheet('Auditoria JSON')
    detail.append(['Respuesta ID','Turno','Modelo evaluado','Indicador','Tipo','Parte','Total partes','JSON UTF-8'])
    for row in indicator_records(payload):
        sheet.append([row[k] for k in ('response_id','turn','model','code','status','score','applicable',
                                      'reader_model','engine','evaluation_id','review_id')])
        text = encoded(row['indicator'])
        chunks = [text[i:i+30000] for i in range(0,len(text),30000)]
        for i, chunk in enumerate(chunks,1):
            detail.append([row['response_id'],row['turn'],row['model'],row['code'],'indicador',i,len(chunks),chunk])
    # Whole persisted result retains observations, counterevidence, provenance and audit
    # that may live above the individual indicator in either family or legacy format.
    for turn in payload.get('results') or []:
        text = encoded(turn.get('evaluation'))
        chunks = [text[i:i+30000] for i in range(0,len(text),30000)]
        for i, chunk in enumerate(chunks,1):
            detail.append([turn.get('response_id'),turn.get('turn_number'),(turn.get('model') or {}).get('name'),
                           None,'evaluacion completa',i,len(chunks),chunk])
    # Prevent formula interpretation of original user/model text or JSON.
    for ws in (sheet, detail):
        for cells in ws.iter_rows():
            for cell in cells:
                if isinstance(cell.value,str):
                    cell.data_type='s'
