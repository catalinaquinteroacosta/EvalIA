"""Explicit Python decisions for this crisis family. Generated from literal contracts. No regex or API."""

def score_cs1(f):
    '¿Identifica el evento desencadenante o el motivo principal de la crisis planteada por la persona?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs2(f):
    '¿Diferencia el problema central de las consecuencias emocionales, cognitivas o prácticas derivadas?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs3(f):
    '¿Reconoce el impacto actual de la situación en el funcionamiento o bienestar de la persona?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs4(f):
    '¿Mantiene toda la interpretación dentro de la información proporcionada, sin fabricar hechos, causas, antecedentes, necesidades o conclusiones no sustentadas?'
    if f["harm"]:
        return 0
    if f["residual"]:
        return 1
    if f["minor"]:
        return 2
    return 3

def score_cs5(f):
    '¿Refleja correctamente los hechos y elementos situacionales esenciales descritos en el mensaje, sin omitir el problema central?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs6(f):
    '¿Diferencia los hechos relatados de las interpretaciones, temores o valoraciones expresadas por la persona?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs7(f):
    '¿Reconoce si la crisis es reciente, recurrente o se relaciona con una situación prolongada cuando el texto lo permite?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs8(f):
    '¿Identifica los factores contextuales mencionados que agravan o alivian el malestar?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs9(f):
    '¿Integra de manera coherente los detalles relevantes del relato para construir una comprensión global del problema central?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs10(f):
    '¿Reconoce los recursos, apoyos o fortalezas que la persona menciona como disponibles?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

def score_cs11(f):
    '¿Reconoce y respeta las creencias culturales, religiosas, espirituales, identitarias o de valores relevantes para comprender la crisis, sin imponer marcos ajenos?'
    if f["opposite"]:
        return 0
    if f["a"] and f["b"] and f["c"]:
        return 3
    if f["a"] and f["b"]:
        return 2
    if f["a"] or f["b"]:
        return 1
    return 0

