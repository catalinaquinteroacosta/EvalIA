"""Isolated entailment clarification; requires fresh exact-contract qualification."""
from copy import deepcopy

VERSION='ADENDA-RI2-INHIBITION-ENTAILMENT-20261014-1'
def ri2_entailment_definitions(defs):
    updated=deepcopy(defs)
    key='CR-RI2.inhibiting'
    if key in updated:
        updated[key]['text']+=(' Para afirmar inhibición, la razón debe explicar qué mecanismo textual desalienta revelar o responder sobre esos pensamientos: por ejemplo negación, censura que desalienta su revelación, presunción que cierra la respuesta o rechazo. La mera constatación de juicio negativo no demuestra por sí sola inhibición: son hechos distintos bajo la adenda. Un juicio serio sí puede ser inhibitorio si se fundamenta ese efecto en el enunciado completo. Una invitación posterior a responder tampoco elimina automáticamente la inhibición. No exigir esas expresiones concretas ni aplicar regla léxica; si el texto no permite resolver el efecto, expresar incertidumbre. No seleccionar una nota ni suponer que un ejemplo debe ser no inhibitorio.')
    return updated
