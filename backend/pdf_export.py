"""Informe de resultados guardados de EvalIA con anexo de auditoría."""
from __future__ import annotations

from html import escape
from io import BytesIO
import re
from pathlib import Path
import reportlab
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

NAVY = colors.HexColor('#172B45')
TEAL = colors.HexColor('#147D82')
SLATE = colors.HexColor('#526476')
PALE = colors.HexColor('#EDF3F6')
LINE = colors.HexColor('#D5E0E7')
FONTS = Path(reportlab.__file__).parent / 'fonts'
pdfmetrics.registerFont(TTFont('EvalIA', str(FONTS / 'Vera.ttf')))
pdfmetrics.registerFont(TTFont('EvalIA-Bold', str(FONTS / 'VeraBd.ttf')))


def safe(value):
    # Word joiners are invisible in the official source; Vera renders them as
    # missing-glyph boxes. Remove only these display controls, never source data.
    text = '—' if value is None or value == '' else str(value)
    text = text.replace('\u2060', '').replace('\ufeff', '')
    return escape(text).replace('\n', '<br/>')


def percent(value):
    if value is None:
        return '—'
    try:
        return f'{float(value):.2f}%'
    except (ValueError, TypeError):
        return str(value)


def alert_text(alert):
    if isinstance(alert, str):
        return alert
    if not isinstance(alert, dict):
        return str(alert)
    name = alert.get('criterion_name') or alert.get('indicator_code') or 'Alerta'
    description = alert.get('message') or alert.get('description') or 'Revisión requerida'
    return f'{name}: {description}'


def indicator_order(item):
    code = item.get('indicator_code') or ''
    match = re.match(r'([^0-9]*)([0-9]+)$', code)
    return (item.get('criterion_code') or '', match.group(1) if match else code,
            int(match.group(2)) if match else 0)


def build_results_pdf(payload: dict) -> bytes:
    """Presenta datos almacenados, sin ejecutar de nuevo el motor de evaluación."""
    experiment = payload['experiment']
    experiment_id = int(experiment['id'])
    conversations = payload.get('conversation_results') or []
    responses = payload.get('results') or []
    summary = payload.get('summary') or {}
    output = BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=(21 * cm, 29.7 * cm),
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=2.1 * cm, bottomMargin=1.75 * cm,
        title=f'EvalIA | Informe del experimento {experiment_id:04d}',
        author='EvalIA', subject='Resultados guardados y trazabilidad de indicadores',
    )
    base = getSampleStyleSheet()
    styles = {
        'kicker': ParagraphStyle('Kicker', parent=base['Normal'], fontName='EvalIA-Bold', fontSize=8, leading=11, textColor=TEAL, spaceAfter=8),
        'title': ParagraphStyle('ReportTitle', parent=base['Normal'], fontName='EvalIA-Bold', fontSize=22, leading=27, textColor=NAVY, spaceAfter=12),
        'section': ParagraphStyle('Section', parent=base['Normal'], fontName='EvalIA-Bold', fontSize=13, leading=17, textColor=NAVY, spaceBefore=16, spaceAfter=7, keepWithNext=True),
        'sub': ParagraphStyle('Subsection', parent=base['Normal'], fontName='EvalIA-Bold', fontSize=10, leading=14, textColor=TEAL, spaceBefore=11, spaceAfter=5, keepWithNext=True),
        'body': ParagraphStyle('ReportBody', parent=base['Normal'], fontName='EvalIA', fontSize=8.7, leading=13, textColor=NAVY, spaceAfter=7, splitLongWords=True),
        'muted': ParagraphStyle('ReportMuted', parent=base['Normal'], fontName='EvalIA', fontSize=8, leading=11.5, textColor=SLATE, spaceAfter=5, splitLongWords=True),
        'cell': ParagraphStyle('ReportCell', parent=base['Normal'], fontName='EvalIA', fontSize=7.8, leading=11, textColor=NAVY, splitLongWords=True),
        'cellbold': ParagraphStyle('ReportCellBold', parent=base['Normal'], fontName='EvalIA-Bold', fontSize=7.8, leading=11, textColor=NAVY, splitLongWords=True),
    }
    story = []

    def para(value, style='body'):
        return Paragraph(safe(value), styles[style])

    def field(label, value):
        story.append(Paragraph(f'<font color="#526476">{safe(label)}</font>  {safe(value)}', styles['body']))

    def grid(headers, rows, widths, compact=False):
        data = [[para(value, 'cellbold') for value in headers]]
        data.extend([[para(value, 'cell') for value in row] for row in rows])
        table = LongTable(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PALE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFB')]),
            ('LINEBELOW', (0, 0), (-1, 0), 0.8, TEAL),
            ('LINEBELOW', (0, 1), (-1, -1), 0.25, LINE),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 4 if compact else 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4 if compact else 6),
        ]))
        story.append(table)

    def list_section(title, values):
        story.append(para(title, 'sub'))
        if not values:
            story.append(para('Sin registros.', 'muted'))
        for value in values:
            story.append(para('• ' + alert_text(value)))

    # Portada y alcance
    story.extend([Spacer(1, 1.1 * cm), para('EVALIA  /  INFORME DE RESULTADOS', 'kicker'),
                  para(f'Experimento {experiment_id:04d}', 'title')])
    story.append(para(experiment.get('scenario_title') or 'Escenario sin título', 'section'))
    story.append(HRFlowable(width='100%', thickness=1.2, color=TEAL, spaceAfter=16))
    field('Código del escenario', experiment.get('scenario_code'))
    field('Rúbrica', experiment.get('rubric_type'))
    field('Estado del experimento', experiment.get('status'))
    field('Respuestas evaluadas', f"{summary.get('responses_evaluated', 0)} de {summary.get('responses_saved', 0)}")
    reviews = sum(1 for turn in responses if (turn.get('evaluation') or {}).get('review_id') is not None)
    if reviews:
        field('Respuestas con revisión guardada', reviews)
        field('Clasificación', 'En revisión; sin resultado global longitudinal')
    field('Modelos con resultado longitudinal', len(conversations))
    if summary.get('responses_pending_evaluation'):
        field('Evaluaciones pendientes', summary['responses_pending_evaluation'])
    story.append(Spacer(1, 0.6 * cm))
    story.append(para('Alcance del documento', 'sub'))
    story.append(para('Este informe transcribe los resultados almacenados por EvalIA. Los puntajes no se recalculan durante la exportación. Las calificaciones automáticas están sujetas a auditoría y validación humana.'))
    story.append(para('Lectura de la escala', 'sub'))
    story.append(para('Los indicadores aplicables se muestran en una escala de 0 a 3. N/A indica que el indicador fue registrado como no aplicable y no equivale a cero. La cobertura informa la proporción de indicadores aplicables.'))

    story.append(PageBreak())
    story.append(para('Comparación de modelos', 'section'))
    if conversations:
        grid(['Modelo', 'Resultado', 'Clasificación', 'Cobertura'], [
            [item.get('model', {}).get('name'), percent(item.get('global_percentage')),
             item.get('classification'), percent((item.get('coverage') or {}).get('percentage'))]
            for item in conversations
        ], [5.1 * cm, 3.2 * cm, 5 * cm, 4.1 * cm])
    else:
        story.append(para('No hay resultados longitudinales guardados.'))
    story.append(para('Las diferencias descriptivas entre modelos no constituyen por sí mismas una prueba de significación estadística.', 'muted'))

    for item in conversations:
        model = item.get('model') or {}
        result = item.get('result') or {}
        story.append(PageBreak())
        story.append(para(f"Modelo  /  {model.get('name') or 'Sin nombre'}", 'section'))
        grid(['Resultado global', 'Clasificación', 'Cobertura', 'Evaluado'], [[
            percent(item.get('global_percentage')), item.get('classification'),
            percent((item.get('coverage') or {}).get('percentage')), item.get('evaluated_at')
        ]], [3.7 * cm, 4.5 * cm, 3.5 * cm, 5.7 * cm])
        field('Proveedor', model.get('provider'))
        story.append(para('Síntesis registrada', 'sub'))
        story.append(para(result.get('executive_summary') or item.get('executive_summary') or 'Sin resumen registrado.'))
        story.append(para('Resultados por criterio', 'sub'))
        criteria = sorted(result.get('criteria') or [], key=lambda c: c.get('order') or 0)
        if criteria:
            grid(['Criterio', 'Nota / 3', 'Resultado', 'Estado'], [
                [f"{c.get('criterion_code') or '—'} · {c.get('criterion_name') or '—'}",
                 c.get('score_0_to_3') if c.get('score_0_to_3') is not None else c.get('rubric_level'),
                 percent(c.get('percentage')), c.get('status') or c.get('classification')]
                for c in criteria
            ], [7.5 * cm, 2.2 * cm, 2.8 * cm, 4.9 * cm], compact=True)
        else:
            story.append(para('No se guardaron criterios longitudinales.', 'muted'))
        list_section('Fortalezas registradas', result.get('strengths') or [])
        list_section('Oportunidades de mejora registradas', result.get('improvement_opportunities') or [])
        list_section('Alertas críticas registradas', result.get('critical_alerts') or [])
        turns = sorted(
            [row for row in responses if (row.get('model') or {}).get('id') == model.get('id')],
            key=lambda row: row.get('turn_number') or 0,
        )
        story.append(para('Conversación y evaluación por turno', 'section'))
        for turn in turns:
            evaluation = turn.get('evaluation') or {}
            turn_result = evaluation.get('result') or {}
            story.append(para(f"Turno {turn.get('turn_number')}", 'sub'))
            story.append(para('MENSAJE DEL USUARIO', 'kicker'))
            story.append(para(turn.get('user_message')))
            story.append(para('RESPUESTA DEL MODELO', 'kicker'))
            story.append(para(turn.get('response_text')))
            if not turn.get('evaluated'):
                story.append(para('Evaluación pendiente.', 'muted'))
                continue
            grid(['Resultado', 'Clasificación', 'Cobertura', 'Fecha'], [[
                percent(evaluation.get('global_percentage')), evaluation.get('classification'),
                percent((evaluation.get('coverage') or {}).get('percentage')), evaluation.get('evaluated_at')
            ]], [3.1 * cm, 4.2 * cm, 3.4 * cm, 6.7 * cm], compact=True)
            if turn_result.get('executive_summary') or evaluation.get('executive_summary'):
                story.append(para('Resumen registrado', 'sub'))
                story.append(para(turn_result.get('executive_summary') or evaluation.get('executive_summary')))
            turn_criteria = sorted(turn_result.get('criteria') or [], key=lambda c: c.get('order') or 0)
            if turn_criteria:
                story.append(para('Criterios del turno', 'sub'))
                grid(['Criterio', 'Nivel', 'Resultado'], [
                    [f"{c.get('criterion_code') or '—'} · {c.get('criterion_name') or '—'}",
                     c.get('rubric_level'), percent(c.get('percentage'))]
                    for c in turn_criteria
                ], [11 * cm, 2.3 * cm, 4.1 * cm], compact=True)
            for title, key in [('Fortalezas del turno', 'strengths'),
                               ('Oportunidades de mejora del turno', 'improvement_opportunities'),
                               ('Alertas críticas del turno', 'critical_alerts')]:
                if turn_result.get(key):
                    list_section(title, turn_result[key])
            story.append(HRFlowable(width='100%', thickness=0.4, color=LINE, spaceBefore=12))

    # Anexo completo de indicadores para auditoría
    story.append(PageBreak())
    story.append(para('Anexo  /  Trazabilidad de indicadores', 'section'))
    story.append(para('Cada fila conserva el código, la nota o N/A y la justificación registrada para un modelo y turno. Falla crítica y prioridad se indican cuando están presentes.'))
    from backend.export_audit import indicator_records, encoded
    records = indicator_records(payload)
    if not records:
        story.append(para('No hay indicadores persistidos para exportar.', 'muted'))
    previous = None
    for record in records:
        identity = (record['response_id'], record['turn'], record['model'])
        if identity != previous:
            story.append(para(f"{record['model']} / Turno {record['turn']} / Respuesta {record['response_id']}", 'sub'))
            field('Lector / motor', f"{record['reader_model']} / {record['engine']}")
            field('Persistencia', f"evaluation_id={record['evaluation_id']}; review_id={record['review_id']}")
            previous = identity
        field('Indicador / estado / nota / aplicabilidad',
              f"{record['code']} / {record['status']} / {record['score'] if record['score'] is not None else 'Sin nota'} / {record['applicable']}")
        # Full native indicator includes decisions, both readers, literal evidence,
        # counterevidence, reasons and provenance. Never replace null with zero/N/A.
        text = encoded(record['indicator'])
        for start in range(0, len(text), 1200):
            story.append(para(text[start:start+1200], 'muted'))

    def page_frame(canvas, pdf_doc):
        canvas.saveState()
        width, height = doc.pagesize
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, height - 1.45 * cm, width - doc.rightMargin, height - 1.45 * cm)
        canvas.setFont('EvalIA-Bold', 7.5)
        canvas.setFillColor(TEAL)
        canvas.drawString(doc.leftMargin, height - 1.25 * cm, 'EVALIA  /  INFORME DE RESULTADOS')
        canvas.setFont('EvalIA', 7.5)
        canvas.setFillColor(SLATE)
        canvas.drawString(doc.leftMargin, 1.0 * cm, f'Experimento {experiment_id:04d} · Datos almacenados')
        canvas.drawRightString(width - doc.rightMargin, 1.0 * cm, f'Página {pdf_doc.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
    return output.getvalue()
