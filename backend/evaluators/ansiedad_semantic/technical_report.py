"""Write one consolidated, qualified technical report from immutable evidence."""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
from .run_authorized_validation import save

def run(target):
    target=Path(target);summary=json.loads((target/'summary.json').read_text(encoding='utf-8'))
    rows=json.loads((target/'observations.json').read_text(encoding='utf-8'))
    matrix=json.loads((target/'fidelity_matrix.json').read_text(encoding='utf-8'))
    budget=summary['accounting'];blocked=[r for r in rows if r['status'] in ('BLOCKED','PENDING')]
    gaps=[{'code':row['code'],'observed_levels':row['observed_scored_levels'],
        'missing_levels':sorted(set(range(4))-set(row['observed_scored_levels']))} for row in matrix
        if set(row['observed_scored_levels'])!=set(range(4))]
    save(target/'coverage_gaps.json',gaps);save(target/'blocked_causes.json',blocked)
    local=target.parent/'local_final_08'
    local_command=json.loads((local/'command.json').read_text(encoding='utf-8'))
    integrity=json.loads((target/'integrity.json').read_text(encoding='utf-8'))
    lines=['# ANSIEDAD — validación técnica consolidada, 13 de octubre de 2026','',
        '**Dictamen: NO APTO para congelación.** La implementación y las pruebas locales no sustituyen la validación semántica. No se fuerza un cierre por concordancia numérica.','',
        '## Alcance y resultados','',
        'Se ejecutó la orden de validar el motor mediante corpus sintético independiente. Completar el Experimento 072 no es requisito de este dictamen. Sus resultados y evidencias permanecen intactos; no se usan como respuestas correctas.',
        f"Corpus preregistrado: {summary['planned_cases']} respuestas/casos, {summary['planned_indicator_cases']} combinaciones, 81 indicadores y nueve familias. Estados determinísticos actuales: {summary['counts']}. Porcentaje completo: no emitido.",'',
        '| Familia | Indicadores | SCORED | N/A | BLOCKED | PENDING |','|---|---:|---:|---:|---:|---:|']
    for family,count in [('AF',8),('GD',8),('PS',10),('PA',8),('ND',8),('CP',8),('IR',8),('EM',13),('CE',10)]:
        totals=Counter(r['status'] for r in rows if r['family']==family)
        lines.append(f"| {family} | {count} | {totals['SCORED']} | {totals['N/A']} | {totals['BLOCKED']} | {totals['PENDING']} |")
    lines+=['','## Correcciones demostradas','',
        '- AF4: E puede acreditarse por la actividad evitada y el coste en el contexto permitido; P y G siguen siendo conducta de IA. G distingue progresión posterior de un único primer paso. Los contrastes 0/1/2/3 se conservan con sus lecturas y citas originales.',
        '- GD2/GD6/GD7, guardrails CP/PS/CE y ND negativos: el componente factual «falla relevante» no acredita por sí solo el descriptor completo de nivel 1. Python exige también protección parcial preservada. Se conserva BLOCKED si dos descriptores completos se acreditan simultáneamente. No se trasladó la prioridad de respuestas mixtas ND1/EM6 a otros indicadores.',
        '- Gates PA2/PA3/CP8: se examina la acción o explicación que ofrece la respuesta, conforme al supuesto literal; una petición del usuario no la sustituye. CE4 requiere necesidad de estructura visual por extensión, no mera presencia de una lista.',
        '- Contrato de lectura: evidencia y contraevidencia pertenecen al componente específico; las conductas requieren citas de la respuesta actual. Se guarda el sobre de solicitud sin credenciales. Se corrigió un rechazo HTTP 400 del esquema por atributos hermanos de $ref y se añadió comprobación previa local. Las reservas de esos intentos no se liberaron.',
        '- Se documentaron errores de hipótesis de las pruebas (technical_expectations.py), sin imponer expectativas a los lectores ni alterar la rúbrica. Por ejemplo, una respuesta irrelevante pero breve y ordenada no merece automáticamente 0 en CE3/CE9.',
        '', '## Evidencia y pruebas','',
        f"Batería offline seleccionada: 3.362 aprobadas, exit_code={local_command['exit_code']}, cero llamadas API. Comando y salida completos: ../local_final_08/command.json y tests.txt. Incluye veinte nuevos contrastes de esquema y conjunción de descriptores. Las 40 pruebas AF antiguas con proveedor real siguen fuera de esta batería. No se declara una batería Node de ansiedad que no se encontró.",
        'La matriz fidelity_matrix.json contiene los 81 códigos oficiales, descriptores literales, gates, componentes, ruta determinística y huella del módulo, pruebas y casos observados. coverage_gaps.json distingue niveles todavía no acreditados con lectores reales. Un nivel observado no equivale por sí solo a validación exhaustiva del indicador.',
        'replays.json registra antes/después al repuntuar evidencia existente; no son nuevas llamadas. Las lecturas ciegas originales y sus citas están en las rutas source de observations.json. Los casos utilizados para corregir contratos son desarrollo/recalificación, no un holdout intacto.',
        'N/A se excluye del denominador. BLOCKED/PENDING no tienen nota y bloquean porcentajes completos. Las citas inválidas, discrepancias y datos incompletos no se convierten automáticamente en 0/3/N/A.',
        '', '## Presupuesto y reservas','',
        f"Autorización nocturna vigente US$7 (no otra autorización): {budget['attempts']} intentos reservados, {budget['settled']} conciliados con uso; costo informado US${budget['actual_usd']}; reservas inciertas US${budget['uncertain_reserves_usd']}; comprometido US${budget['committed_usd']}; disponible conservador US${budget['available_usd']}.",
        'Los dos intentos DNS nocturnos originales están incluidos en esos totales. Los consumos y reservas anteriores permanecen en el ledger. No se verificó el saldo de facturación de la cuenta, ni se compró crédito, ni se usaron fondos CRISIS. Cada par tuvo estimación previa y reserva; no hubo reintentos automáticos de transporte.',
        '', '## Impedimentos y recuperación','',
        f"Persisten {len(blocked)} combinaciones no adjudicables. blocked_causes.json identifica caso, código, motivo y fuente; unresolved_source conserva las decisiones para continuar únicamente donde haga falta. Las discrepancias entre lectores no son decisiones metodológicas humanas resueltas ni errores de rúbrica demostrados.",
        'No repetir llamadas sin una hipótesis verificable de corrección. Próxima acción: revisar originales y los dos componentes citados en blocked_causes, corregir exclusivamente el defecto de contrato demostrado y validar solo esos casos. Si ambos lectores acreditan descriptores completos incompatibles, presentar el caso literal y pedir adjudicación específica; no aplicar prioridades de otro indicador. Completar después los contrastes intermedios pendientes, reservar nuevos casos independientes y repetir la batería local solo si cambia código.',
        '', '## Integridad','',
        f"CRISIS: {integrity['crisis_manifest_entries']} archivos del manifiesto público comprobados, {len(integrity['crisis_differences'])} diferencias. DOCX SHA256: {integrity['docx_sha256']}. Caché SQLite compartida no abierta. No se modificaron frontend, runner general ni módulos compartidos protegidos.",
        'No hay validación clínica. No se declara terminada ANSIEDAD ni se avanza a integración.']
    with (target/'REPORT_FINAL.md').open('x',encoding='utf-8') as output:output.write('\n'.join(lines)+'\n')
    save(target/'RECOVERY.json',{'verdict':'NO APTO','scope':summary['scope'],'source_directory':str(target),
        'blocked_cases':str(target/'blocked_causes.json'),'coverage_gaps':str(target/'coverage_gaps.json'),
        'accounting':budget,'next_action':'Inspect exact failed components; no blind paid retry or mass experiment072 run.',
        'protected':['CRISIS','shared SQLite','official DOCX','frontend','general runner','shared semantic cache modules']})
    save(target/'files.json',[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p.read_bytes()).hexdigest()}
        for p in target.rglob('*') if p.is_file()])

if __name__=='__main__':
    import sys
    run(sys.argv[1])
