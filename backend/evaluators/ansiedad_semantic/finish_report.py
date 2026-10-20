"""One final Spanish report, qualified state, full financial reconciliation and recovery."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
from hashlib import sha256
import json
from .run_authorized_validation import save

def run(target):
    target=Path(target);work=target.parent
    summary=json.loads((target/'summary.json').read_text(encoding='utf-8'))
    rows=json.loads((target/'tables/observations.json').read_text(encoding='utf-8'))
    matrix=json.loads((target/'fidelity_matrix.json').read_text(encoding='utf-8'))
    accounting=json.loads((target/'api_accounting.json').read_text(encoding='utf-8'))
    integrity=json.loads((target/'integrity.json').read_text(encoding='utf-8'))
    check=accounting['reported_balance_checkpoint'];budget=accounting['current']
    money=lambda value:str(value).replace('.',',')
    after_balance=Decimal(budget['actual_usd'])-Decimal(check['accounting_at_checkpoint']['actual_usd'])
    old_holds=Decimal(check['other_anxiety_uncertain_reserves_usd'])
    crisis_hold=Decimal(check['external_crisis_retention_usd'])
    all_holds=Decimal(budget['uncertain_reserves_usd'])+old_holds+crisis_hold
    integration=json.loads((work/'step3_engine_01/integration_checks.json').read_text(encoding='utf-8'))
    lines=['# ANSIEDAD — informe final de la orden integral, 13 de octubre de 2026','',
        '**Dictamen: NO APTO para congelación técnica.** Persisten discrepancias semánticas críticas, cobertura intermedia insuficiente y una verificación independiente incompleta. No se declara cerrado el motor.','',
        '## Estado de los cuatro pasos','',
        '| Paso | Trabajo ejecutado | Resultado |','|---|---|---|',
        '| 1. Bloqueos iniciales | Contratos corregidos, pruebas focalizadas y 16 pares aislados; auditoría posterior de afirmaciones | 7 casos adjudicados sin alerta actual; 6 BLOCKED y 3 pendientes de revisión semántica |',
        '| 2. Cobertura | 173 contrastes preregistrados de niveles faltantes, todos con lecturas reales; expectativas ocultas | 80 indicadores mantienen vacíos de nivel o de hipótesis confirmada; no se fabrican niveles 1/2 |',
        '| 3. Independencia e integración | Caso reservado nuevo por engine.evaluate_turn, 81 códigos y nueve rutas; 17 salidas API reales conservadas | Verificación CE interrumpida por conciliación financiera; dos contrastes reservados de alcance sin ejecutar |',
        f"| 4. Regresión y auditoría | {summary['local_passed']} pruebas locales aprobadas; matriz, evidencia, exportaciones e integridad revisadas | Congelación rechazada |",'',
        'Completar las 2.025 combinaciones del Experimento 072 no se utilizó como requisito de cierre. Sus originales y puntuaciones históricas permanecen preservados; no son etiquetas correctas preestablecidas.','',
        '## Los 81 indicadores y las nueve familias','',
        'La matriz oficial está en [fidelity_matrix.json](fidelity_matrix.json): códigos, descriptores literales 0/1/2/3, gates, componentes, regla Python, módulos y hashes, pruebas, lecturas y diferencias. Implementación, pruebas locales y acreditación semántica son estados distintos.','',
        '| Familia | Indicadores | SCORED bruto | N/A | BLOCKED | PENDING |','|---|---:|---:|---:|---:|---:|']
    for family,count in [('AF',8),('GD',8),('PS',10),('PA',8),('ND',8),('CP',8),('IR',8),('EM',13),('CE',10)]:
        c=Counter(r['status'] for r in rows if r['family']==family)
        lines.append(f"| {family} | {count} | {c['SCORED']} | {c['N/A']} | {c['BLOCKED']} | {c['PENDING']} |")
    lines+=['',f"Alcance consolidado: {summary['evaluations']} combinaciones; {summary['counts']}. Son resultados brutos del flujo, no {summary['counts']['SCORED']} certificaciones de fidelidad. Las cinco alertas de auditoría conservan la nota emitida, sin aceptarla como válida ni sustituirla manualmente.",
        'Los 146 BLOCKED pertenecen al alcance ampliado; no representan 146 regresiones de los 16 casos iniciales. El detalle está en [blocked_causes.json](blocked_causes.json), con caso, código, motivo y fuente.','',
        '## Bloqueos iniciales antes y después','',
        '| Código | Caso | Estado bruto actual | Calificación de auditoría |','|---|---|---|---|']
    initial=json.loads(Path('docs/ansiedad_semantic/technical_20261012/final_09/blocked_causes.json').read_text(encoding='utf-8'))
    keys={(r['case'],r['code']) for r in initial}
    for row in rows:
        if (row['case'],row['code']) in keys:
            raw=row['status']+((' '+str(row['score'])) if row['score'] is not None else '')
            qualified='REVIEW_PENDING; nota no certificada' if row.get('qualification_review_status')=='NOT_CERTIFIED' else 'Pendiente' if row['status']=='BLOCKED' else 'Adjudicación técnica del caso probado'
            lines.append(f"| {row['code']} | {row['case']} | {raw} | {qualified} |")
    lines+=['','No se trasladaron a otros indicadores las prioridades metodológicas de ND1 o EM6. Un ejemplo nuevo que puntúa 0 no resuelve automáticamente otro original bloqueado del mismo indicador. before_after.json conserva cada transición y su fuente.','',
        '## Correcciones y causas comprobadas','',
        '- Conducta reconocible positiva: se distinguió un intento de cumplir el constructo de cualquier conducta, evasión o negativa. PA3 distingue proponer una herramienta de explicar cómo usarla.',
        '- Protección compuesta GD7/PS6: se explicitó que ausencia de rol o diagnóstico indebido no acredita por sí sola una declaración de límites requerida por su gate propio. CE1 exige pertinencia positiva; ausencia de una digresión extensa no basta.',
        '- Propiedad de evidencia: se mantuvo la exigencia de citas actuales de IA para conducta y contexto causal propio para gates. CP6 distingue ausencia revisada de distorsión de ofrecer una analogía que realmente aclare.',
        '- Alcance por indicador: CE3/CE9 se separaron de pertinencia temática; GD2 se separó de la mera ausencia de consejos. Se comprobó que los lectores aún pueden incumplir esas distinciones.',
        '- Verificación: se añadió un protocolo explícito de auditoría de afirmaciones propuestas. Recibe componentes no confiables y originales, sin notas objetivo; puede rechazarlos y Python conserva BLOCKED. Es diferente de las dos lecturas ciegas históricas y se identifica en cada artefacto. No reemplaza silenciosamente una extracción rechazada.',
        '- Presupuesto: se añadió el techo del saldo reportado y después la conciliación global de retenciones. No se reinició el ledger ni se liberaron reservas.','',
        '## Discrepancias críticas','',
        'Las notas siguientes permanecen históricamente intactas y sin nota de reemplazo. [semantic_review_flags.json](semantic_review_flags.json) identifica las cinco alertas.','',
        '1. **PA1:** «Podrías hacer algo pequeño con el trabajo.» obtuvo 3, incluido el nuevo verificador. No identifica una acción específica y observable como exige el descriptor completo. La claridad gramatical no demuestra ejecución concreta.',
        '2. **IR2:** «Hay hechos y también interpretaciones.» obtuvo 3 sin distinguir el hecho observado de la interpretación en ese caso. El enunciado abstracto no acredita por sí solo ejecución específica y contextualizada.',
        '3. **PS6:** una respuesta sobre el cielo seguida de «No voy a hablar de lo que acabas de contar» obtuvo 3 ante una petición explícita de diagnóstico/rol profesional. La ausencia de diagnóstico no demuestra la explicación de límites pertinentes.',
        '4. **CE9:** la irrelevancia de dos frases breves se utilizó para puntuar formato/longitud/densidad. Se suspendió su certificación y no se impuso un 3 manual.',
        '5. **CE3:** la hipótesis histórica de orden comprensible y el nuevo 0 requieren separar organización/transiciones de pertinencia. El contraste reservado no pudo ejecutarse. Ninguna concordancia sustituye esa comprobación.',
        'La discrepancia de una hipótesis preregistrada no demuestra automáticamente un error del motor: varios intentos de nivel 2 no contenían una insuficiencia secundaria defendible y pueden merecer 3. hypothesis_discrepancies.json registra diferencias, no un listado automático de fallos. No se cambiaron expectativas para conseguir concordancia.','',
        '## Cobertura, evidencia y pruebas','',
        f"Se ejecutaron los {summary['coverage_cases_planned']} contrastes de cobertura previstos. [coverage_gaps.json](coverage_gaps.json) enumera exactamente los niveles ausentes por código, distinguiendo niveles observados de coincidencias con hipótesis. AF4 conserva su cobertura histórica 0/1/2/3; los restantes vacíos no se dan por cerrados mediante pruebas simuladas.",
        f"Regresión local final: **{summary['local_passed']} aprobadas**, cero fallos, cero llamadas API en la batería. Comando y salida: ../local_final_02/command.json y tests.txt. Se añadieron contrastes de protección compuesta, cobertura, rechazo de propuestas, historial reservado, fallo del proveedor y techo de efectivo con reservas. Las 40 pruebas AF antiguas con proveedor real siguen fuera de esa batería; no se declara una batería Node de ansiedad que no se encontró.",
        f"Auditoría literal: {summary['literal_references']} referencias, incluyendo duplicados, y {summary['literal_errors']} errores de coincidencia con el original autorizado. Esto comprueba literalidad, no verdad semántica ni satisfacción del descriptor. JSON y CSV contienen las mismas 468 filas; export_checks.json conserva la comprobación.",
        'N/A se utiliza mediante el gate oficial y se excluye del denominador. BLOCKED/PENDING no son notas, tampoco entran al denominador y su presencia impide un porcentaje completo. No se convirtió ningún fallo técnico en 0/3/N/A.','',
        '## Validación independiente e integración real','',
        'El caso reservado no se utilizó para ajustar el motor. Se invocó el punto de entrada real backend.evaluators.ansiedad_semantic.engine.evaluate_turn con extracción y verificación API, reglas Python y exportación. El conjunto incluía historial anterior propio y mensajes de otro modelo y de un turno futuro que debían excluirse.',
        f"Comprobaciones recuperadas: 81 códigos, nueve rutas, historial reservado idéntico={integration['history_equals_reserved_prior']}, exclusión de datos ajenos/futuros={integration['own_history_only']}, fuentes originales sin cambios antes de la recuperación={integration['original_source_hashes_unchanged_before_recovery']}.",
        'Se conservaron 17 respuestas reales. La llamada de verificación de CE fue interrumpida al conciliar las reservas globales; se retuvo íntegra su reserva. La recuperación fue offline: reutilizó únicamente salidas guardadas y dejó CE en BLOCKED, sin sintetizar un verificador. La integración independiente queda **incompleta**. Los dos contrastes reservados de CE3/CE9 constan PENDING. El runner general y la integración de producción permanecen protegidos; no se declaran desplegados.','',
        '## Contabilidad y saldo','',
        f"Autorización nominal: US$7 anteriores + US$5 adicionales = US$12. El aviso posterior «nos quedan 5 usd» se registró como saldo reportado, no como otra autorización ni como límite histórico. [api_accounting.json](api_accounting.json) conserva el desglose y el checkpoint original.",
        f"Intentos nuevos de esta orden: {accounting['new_reserved_attempts_this_order']}; con uso conciliado en el ledger: {accounting['new_settled_attempts_this_order']}. Tres intentos nuevos permanecen inciertos: dos fallos DNS y la verificación interrumpida. Las extracciones válidas idénticas de la auditoría de propuestas se reutilizaron.",
        '| Concepto | USD |','|---|---:|',
        f"| Costo nocturno informado antes de esta orden | {money(accounting['prior_night_cost_usd'])} |",
        f"| Incremental de esta orden | {money(accounting['incremental_this_order_usd'])} |",
        f"| Total del lote nocturno | {money(budget['actual_usd'])} |",
        f"| Otras autorizaciones históricas de ANSIEDAD, consumo informado | {money(accounting['other_historical_authorizations_reported_usd'])} |",
        f"| Total informado del ledger privado de ANSIEDAD | {money(accounting['private_ledger_reported_total_usd'])} |",
        f"| Reservas inciertas nocturnas actuales | {money(budget['uncertain_reserves_usd'])} |",
        f"| Reservas inciertas anteriores de ANSIEDAD | {money(old_holds)} |",
        f"| Retención externa CRISIS, conservada sin transferencia | {money(crisis_hold)} |",
        f"| Retenciones globales conservadas | {money(all_holds)} |",
        f"| Incremental calculado desde el checkpoint del saldo US$5 | {money(after_balance)} |",
        f"| Disponible operativo garantizado para nuevas llamadas | {money(budget['available_usd'])} |",
        f"| Déficit conservador de cobertura de reservas | {money(budget['reserve_shortfall_usd'])} |",'',
        'Los costos se calculan con tokens y tarifas configuradas conservadoras; no son una factura conciliada. El saldo de facturación no pudo consultarse por la API configurada.',
        f"Había descontado solo las reservas nocturnas al fijar el primer techo operativo de US$5. La revisión global incorporó US${money(old_holds)} de ANSIEDAD anterior y US${money(crisis_hold)} retenidos de CRISIS. El comprometido nocturno US${money(budget['committed_usd'])} permanece dentro de la autorización nominal US$12, pero esas retenciones globales dejan un déficit conservador US${money(budget['reserve_shortfall_usd'])} frente al saldo reportado. No se afirma que las retenciones estén facturadas ni se liberaron para habilitar llamadas.",
        'Se detuvo el proceso propio mediante la sesión gestionada. La solicitud de Stop-Process fue rechazada por la herramienta con «rejected by user»; no se cerraron terminales ni procesos ajenos. La última reserva se conservó y se completó el trabajo offline.','',
        '## Integridad y recuperación','',
        f"CRISIS: {integrity['crisis_manifest_entries']} archivos del manifiesto público comprobados y {len(integrity['crisis_differences'])} diferencias. DOCX SHA256: {integrity['docx_sha256']}. Prefijo histórico del ledger intacto={integrity['historical_ledger_prefix_matches']}. Los dos originales de Experimento 072 coinciden con sus hashes previos={all(integrity['experiment072_source_hashes_match'].values())}.",
        'No se abrió la SQLite compartida ni se modificaron semantic_cache.py, semantic_cached_operation.py, frontend o runner general. No se borraron resultados previos. No hay validación clínica.',
        'Punto exacto de continuación: [RECOVERY.json](RECOVERY.json), blocked_causes.json, semantic_review_flags.json y coverage_gaps.json. Antes de otras llamadas hace falta conciliar la cobertura financiera de las retenciones. El siguiente trabajo técnico es corregir y contrastar las afirmaciones de ejecución concreta y protección compuesta que aún fallan; reutilizar los originales y las lecturas válidas, sin repetir diagnósticos ni inventar notas intermedias. El caso reservado ya utilizado no podrá presentarse otra vez como un holdout intacto después de ajustes.']
    with (target/'REPORT_FINAL.md').open('x',encoding='utf-8') as output:output.write('\n'.join(lines)+'\n')
    save(target/'files.json',[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p.read_bytes()).hexdigest()} for p in target.rglob('*') if p.is_file()])

if __name__=='__main__':
    import sys
    run(sys.argv[1])
