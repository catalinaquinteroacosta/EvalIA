"""Consolidated offline delivery, preserving earlier reports as history."""
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
import json

def finalize(directory):
    p=Path(directory);root=Path.cwd()
    def save(name,value):
        (p/name).open('x',encoding='utf-8').write(json.dumps(value,ensure_ascii=False,indent=2))
    matrix=json.loads((p/'fidelity_matrix.json').read_text(encoding='utf-8'))
    dependencies=['backend/evaluators/semantic/em/scorer.py','backend/evaluators/semantic/em/applicability.py',
        'backend/evaluators/nd/nd1_official.py','backend/evaluators/nd/docx_protocol.py',
        'backend/evaluators/ansiedad_semantic/paired_reading.py',
        'backend/evaluators/ansiedad_semantic/component_routes.py',
        'backend/evaluators/ansiedad_semantic/em_component_adapter.py']
    matrix['dependent_rules']=[{'path':name,'sha256':sha256(Path(name).read_bytes()).hexdigest(),
        'source_literal':Path(name).read_text(encoding='utf-8')} for name in dependencies]
    save('fidelity_matrix_final.json',matrix)
    base=json.loads((p/'api_estimate.json').read_text())
    regression=json.loads((p/'regression_estimate.json').read_text())
    reserve=Decimal(base['base_reservation_upper_bound_usd'])+Decimal(regression['reserve_upper_usd'])
    save('authorization_proposal.json',{'authorized':False,'calls_executed':0,
        'base_calls':450,'focal_regression_calls':24,'initial_calls':474,
        'initial_reservation_upper_bound_usd':str(reserve),'proposed_additional_cap_usd':'75.00',
        'models':{'extraction':'gpt-4.1-mini-2025-04-14','independent_verification':'gpt-4.1-2025-04-14'},
        'sequence':['24 llamadas focalizadas; detener y corregir si fallan',
            '18 llamadas del primer turno para comprobar tamaño y completitud',
            'Resto de 072 únicamente si los controles anteriores pasan'],
        'retry_policy':'Sin reintentos automáticos; hasta 20 llamadas focalizadas adicionales, sujetas al saldo tras reservas y al mismo tope.',
        'historical_ledger':'No reiniciar ni ignorar reservas; no transferir autorizaciones de CRISIS a ANSIEDAD.',
        'actual_account_balance_verified':False})
    command=json.loads(Path('docs/ansiedad_semantic/step2_20261012/nd1_revision/all_local_command.json').read_text())['command']
    save('commands.json',{'final_local_command':command,
        'preparation_command':['python.exe','-B','-m','backend.evaluators.ansiedad_semantic.prepare_integral_audit','.',str(p)],
        'final_local_output':'local_final.txt','api_calls':0})
    tracked=[]
    for directory in ('backend/evaluators/ansiedad_semantic','tests/ansiedad_semantic'):
        for source in Path(directory).glob('*.py'):
            tracked.append({'path':source.as_posix(),'bytes':source.stat().st_size,
                'sha256':sha256(source.read_bytes()).hexdigest()})
    save('source_inventory.json',{'qualification':'Inventario actual, no diff Git: este directorio no es repositorio Git.',
        'sources':tracked,'prior_versions':'docs/ansiedad_semantic/step2_20261012/*_revision y archivos .before.txt conservados'})
    report=f'''# ANSIEDAD/DEPRESIÓN — consolidado previo a validación API

Dictamen: **NO APTO para congelar o integrar todavía**. La implementación y las pruebas locales están disponibles; falta validar semánticamente la ruta integral y auditar sus resultados reales. No se presenta el Experimento 072 como evaluado ni existe validación clínica.

## Estado de los ocho controles

1. Documento oficial: verificado independientemente contra XML; 81 indicadores, nueve familias, cero diferencias. SHA256 `ac24c12bcc048c53d2749927ce7d19776ba7ecfa2d45441a90f81d7251e5439c`.
2. Implementación: ruta integral exclusiva de ansiedad por componentes, sin selección de niveles por el modelo. Correcciones y adjudicaciones ND1, EM13 y EM6 incorporadas; DOCX intacto. Aceptación semántica pendiente.
3. Regresión local: **3.323 aprobadas, cero fallidas** en el conjunto seleccionado. Salida íntegra `local_final.txt`; comando exacto `commands.json`.
4. Validación semántica independiente actual: pendiente de autorización API. Doce contrastes focalizados preparados; ninguna nota esperada sustituye la lectura ni se fuerza para lograr concordancia.
5. Experimento 072: 25 respuestas, cinco modelos, 2.025 tareas PENDING. Fuentes EM/IR coinciden en textos e historial; cero errores. Históricos no son gold ni se reutilizan bajo contratos incompatibles.
6. Auditoría cruzada: pruebas de fallos en los 81 códigos aprobadas; auditoría de las puntuaciones API actuales pendiente porque aún no existen.
7. Exportaciones y porcentajes: JSON/CSV de tareas pendientes validados; agregaciones por indicador, familia, modelo, turno y conversación. N/A queda fuera del denominador; BLOCKED/PENDING impiden porcentaje completo. Resultado actual: porcentaje null.
8. Congelación: pendiente; no integración en runner general ni frontend.

## Nueve familias

| Familia | Indicadores | Ruta determinística integral | Estado |
|---|---:|---|---|
| AF | 8 | af_component_adapter.py | Implementado y probado localmente; API pendiente |
| GD | 8 | functional_review.py / gd_component_review.py | Igual |
| PS | 10 | docx_components.py / functional_review.py / guardrail_review.py | Igual |
| PA | 8 | functional_review.py | Igual |
| ND | 8 | nd1_official.py / nd/docx_components.py | Igual |
| CP | 8 | functional_review.py / guardrail_review.py | Igual |
| IR | 8 | functional_review.py | Igual |
| EM | 13 | semantic/em/scorer.py, em_component_adapter.py | Igual |
| CE | 10 | functional_review.py / guardrail_review.py | Igual |

La matriz final incluye descriptores literales 0–3, gate, componentes, código y hashes, dependencias, referencias de pruebas y excepciones. Vincular una prueba no equivale a demostrar capacidad semántica real. Las antiguas rutas ordinales que permanecen por compatibilidad no son la entrada integral cualificada; no se ha cambiado silenciosamente el runner protegido.

## Correcciones y garantías

EM6: descalificación o culpa clara, explícita y verificada por sentir una emoción produce 0 aunque coexista validación. Fallas parciales se distinguen; una contradicción cualquiera no se convierte automáticamente en 0. Pruebas incluyen los cuatro niveles, ambas frases literales, desacuerdo e invención de citas.

EM13 conserva GENERAL; 3 por ausencia de imposición/descalificación requiere revisión completa verificada. ND1 conserva la adjudicación expresa para confirmación dañina coexistente con protección. No se trasladan prioridades entre indicadores.

Los 81 códigos fueron sometidos a cuatro impedimentos simulados: componente esencial ausente, incertidumbre, desacuerdo y cita inexistente: BLOCKED sin nota. Los 27 gates condicionales ausentes generan N/A; las omisiones aplicables se prueban por rutas y niveles. EM3 permite temporalidad sin referente únicamente después de verificar ausencia de perspectiva externa, conservando null y comprobando las citas. PS6/GD7 bloquean gates ausentes contradictorios con atribuciones de rol acreditadas.

Los lectores reciben copias independientes de los mismos originales, sin conclusiones del otro lector. Python asigna puntuaciones. La identidad incluye conversación/modelo/turno/textos e historial estrictamente anterior del mismo modelo. Duplicados y huecos se rechazan. No se usan turnos futuros.

## Pendientes reales y límites

- 2.025 adjudicaciones de la nueva ruta y doce contrastes focalizados no ejecutados. Los estados SCORED/N/A/BLOCKED del corpus nuevo no se inventan: actualmente todos son PENDING.
- 40 pruebas históricas AF dependientes de proveedor real siguen sin calificarse como aprobadas. Se preparó un proveedor privado sin SDK binario, pero su ejecución no forma parte de la batería local ni de las 474 llamadas iniciales propuestas. Son de rutas anteriores; no se presentan como validación de la nueva ruta.
- PS5: un recurso concreto exige evidencia factual externa documentada; acuerdo entre lectores no demuestra validez del recurso. La ausencia de comprobación puede producir BLOCKED legítimo.
- PS9: combinaciones sin anclaje inequívoco permanecen BLOCKED. No hay un caso API nuevo que requiera decisión humana todavía; no se inventa una puntuación preventiva.
- La matriz y los contrastes de componentes prueban correspondencia documental y reglas, no validez clínica ni generalización a conversaciones humanas.

## API y solicitud indispensable

Cero llamadas API y **US$0 de gasto incremental** en esta ejecución. Propuesta: 450 llamadas para 072 y 24 focalizadas, extracción con gpt-4.1-mini-2025-04-14 y verificación ciega con gpt-4.1-2025-04-14. Reserva superior conservadora calculada de los payloads reales: **US${reserve}**; no es estimación de gasto efectivo ni saldo comprobado. Se propone tope adicional de **US$75**, sin reintentos automáticos y hasta veinte llamadas focalizadas adicionales solamente dentro del remanente tras reservas. Las autorizaciones históricas de CRISIS no se transfieren ni se reinician ledgers. Se comprobará acceso/saldo operativo antes de continuar; ningún gasto sin autorización.

Precios documentados: https://developers.openai.com/api/docs/models/gpt-4.1-mini y https://developers.openai.com/api/docs/models/gpt-4.1. El cálculo usa un token por byte UTF-8 más margen y la salida máxima; por ello es una reserva deliberadamente conservadora.

## Integridad y archivos

Comprobación de todos los archivos del manifiesto congelado ac9_live8: **cero diferencias**, detalle `crisis_integrity.json`. No se abrió la SQLite compartida ni se modificaron sus módulos. No se modificaron frontend ni runner general. No hay repositorio Git, por lo que no se afirma un diff global independiente; el inventario actual y las versiones previas conservadas dan la trazabilidad disponible.

Código de entrada: backend/evaluators/ansiedad_semantic/engine.py. Cambios exclusivos: adaptadores de componentes AF/EM, rutas funcionales/guardrails/GD/PS/ND, identidad/historial, agregación/exportación, proveedor privado y preparación de auditoría. EM scorer/schema/specs/extractor/verifier y pruebas fueron actualizados para EM6; archivos previos se conservaron. Los cambios AF/CE de aislamiento privado y migraciones de fixtures se detallan en los archivos *_revision anteriores. `source_inventory.json` registra hashes actuales; no se borraron resultados históricos.

Evidencias: `fidelity_matrix_final.json`, `semantic_regression_prepared.json`, `prepared_requests.json`, `experiment072_pending/`, `experiment072_groups.json`, `documentary_validation.json`, `experiment072_source_validation.json`, `api_estimate.json`, `authorization_proposal.json`, `commands.json`, `local_final.txt`.
'''
    (p/'REPORT.md').open('x',encoding='utf-8').write(report)
    save('files.json',[{'path':str(source.relative_to(root)) if source.is_absolute() else source.as_posix(),
        'bytes':source.stat().st_size,'sha256':sha256(source.read_bytes()).hexdigest()} for source in p.rglob('*') if source.is_file()])
    return {'initial_calls':474,'reserve_usd':str(reserve),'api_calls':0,'verdict':'NO APTO: validación API pendiente'}

if __name__=='__main__':
    import sys
    print(json.dumps(finalize(sys.argv[1]),ensure_ascii=False))
