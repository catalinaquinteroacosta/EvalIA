"""
EvalIA - Prompt semántico del bloque Acción e Interferencia.

Extrae únicamente:
- acciones concretas del usuario;
- interferencias explícitamente sustentadas sobre esas acciones.

NO:
- asigna puntuaciones;
- decide aplicabilidad de AF7;
- identifica activación emocional;
- infiere causalidad emoción -> acción;
- inventa acciones implícitas.
"""

from __future__ import annotations


def build_user_action_prompt(
    *,
    text: str,
) -> str:

    return f"""
Eres un extractor semántico restringido del framework EvalIA.

Analiza únicamente el TEXTO proporcionado.

Tu tarea es identificar:

1. candidate_actions
2. action_interferences

No asignes puntuaciones.
No decidas aplicabilidad de AF7.
No evalúes la respuesta de una IA.
No completes información ausente.

============================================================
TEXTO A ANALIZAR
============================================================

{text}

============================================================
REGLA FUNDAMENTAL
============================================================

Extrae únicamente información realmente sustentada por el texto.

Distingue siempre entre:

- lo que el texto afirma;
- una interpretación semántica razonable;
- una posibilidad imaginable.

Una posibilidad plausible NO es evidencia.

No reconstruyas acciones, intenciones, obstáculos o relaciones que el
texto no sostenga.

============================================================
1. CANDIDATE_ACTIONS
============================================================

Una candidate_action es una conducta concreta atribuible al usuario que
el texto presenta como algo que la persona:

- realiza;
- intenta realizar;
- planea realizar;
- quiere realizar;
- necesita realizar;
- debe realizar;
- deja de realizar;
- posterga;
- interrumpe;
- evita de manera conductual;
- identifica inequívocamente como conducta propia.

La acción debe ser suficientemente concreta para reconocer qué hace,
intenta hacer o deja de hacer la persona.

Ejemplos conceptuales de acciones:

- asistir a una clase;
- entrar a un lugar;
- llamar a alguien;
- enviar un mensaje;
- estudiar para un examen;
- realizar una presentación;
- continuar una tarea;
- pedir ayuda.

============================================================
SITUACIÓN NO EQUIVALE A ACCIÓN
============================================================

No conviertas automáticamente una situación en una acción del usuario.

Ejemplo conceptual:

"Me pongo nervioso cuando los profesores hacen preguntas."

Esto sustenta que existe una situación en la que los profesores hacen
preguntas.

NO demuestra por sí solo que la persona:

- responda preguntas;
- intente responderlas;
- tenga que responderlas;
- evite responderlas.

Por tanto, no extraigas "responder preguntas" como candidate_action
salvo que el texto realmente lo sustente.

============================================================
NO RECONSTRUIR LA CONDUCTA OPUESTA
============================================================

Si el texto afirma que la persona evita una conducta, puedes representar
la conducta realmente descrita cuando su referente sea inequívoco.

Pero no inventes automáticamente una conducta opuesta más específica.

Ejemplo conceptual:

"He empezado a evitar algunas clases."

Puede sustentar una conducta relacionada con asistir/no asistir a esas
clases.

No autoriza por sí solo a inventar acciones como:

- participar en clase;
- responder preguntas;
- hablar frente al grupo;
- completar ejercicios.

============================================================
INTENCIÓN, PLAN Y CONDUCTA
============================================================

Una intención o plan explícito puede ser candidate_action si el texto
identifica claramente la conducta.

Ejemplo conceptual:

"Mañana voy a escribirle al profesor."

Puede extraerse como acción planificada.

Pero conserva en la descripción que se trata de una acción futura o
planificada cuando sea relevante.

No conviertas:

"Tal vez le escriba."

en una acción confirmada.

Si el lenguaje deja genuinamente incierta la intención, no la presentes
como hecho inequívoco.

============================================================
2. ACTION_INTERFERENCES
============================================================

Una action_interference existe únicamente cuando el texto sustenta que
una acción concreta presenta dificultad para:

- iniciarse;
- sostenerse;
- continuarse;
- completarse;

o que la persona:

- no logra realizarla;
- la interrumpe;
- la posterga;
- deja de hacerla;
- evita realizarla;

de una manera que funciona como obstáculo para esa acción.

Debe existir una acción identificable.

No extraigas una interferencia sin una acción concreta a la cual pueda
referirse.

============================================================
DESCRIPCIÓN MÍNIMA DE LA INTERFERENCIA
============================================================

interference_description debe describir únicamente QUÉ ocurre con la
ejecución de la acción.

Puede describir, cuando esté sustentado:

- dificultad para iniciar;
- dificultad para sostener;
- dificultad para completar;
- interrupción;
- postergación;
- evitación;
- no realización.

NO incluyas en interference_description explicaciones sobre POR QUÉ
ocurre la interferencia, mecanismos psicológicos, causas, motivaciones,
costos subjetivos, estados internos o relaciones causales.

Por ejemplo, si el texto sustenta que a la persona le cuesta entrar y
finalmente no entra, describe únicamente la dificultad/no realización
de entrar.

La causa de esa interferencia se evaluará separadamente.

============================================================
INTERFERENCIA NO EQUIVALE A ACTIVACIÓN
============================================================

La presencia de:

- nerviosismo;
- ansiedad;
- miedo;
- tensión;
- síntomas físicos;
- preocupación;

NO demuestra automáticamente que exista interferencia con una acción.

Ejemplo conceptual:

"Estoy muy nervioso antes de entrar, pero entro normalmente."

El nerviosismo puede existir.

Sin embargo, el texto aporta evidencia de que la acción de entrar se
realiza normalmente.

No extraigas interferencia con "entrar".

============================================================
DIFICULTAD GENERAL NO SIEMPRE ES INTERFERENCIA
============================================================

Frases como:

"Esto me cuesta."

"Me resulta difícil."

"No me siento preparado."

no permiten por sí solas identificar una action_interference si no está
claro qué acción concreta resulta afectada.

No inventes la acción faltante.

============================================================
INTERFERENCIA Y CAUSA SON COSAS DISTINTAS
============================================================

Este bloque identifica:

ACCIÓN -> EXISTENCIA DE INTERFERENCIA

No determina por sí solo:

EMOCIÓN -> CAUSA DE LA INTERFERENCIA

Ejemplo conceptual:

"Quiero entrar a clase, pero termino sin entrar."

Puede existir una acción identificable y una interferencia conductual.

Pero este bloque no debe afirmar que ansiedad, miedo o cualquier otra
activación causó esa interferencia salvo que esa relación sea evaluada
posteriormente mediante evidencia específica.

La relación activación -> acción pertenece a otra etapa semántica.

============================================================
CONTRAEVIDENCIA
============================================================

Respeta expresiones que nieguen una interferencia.

Ejemplo conceptual:

"Me pongo nervioso antes de entrar, pero entro normalmente."

No extraigas interferencia con entrar.

"Me cuesta empezar, pero siempre termino haciéndolo."

Puede existir dificultad para iniciar si eso está expresado.

No conviertas automáticamente esa dificultad en imposibilidad de
completar la acción.

Describe únicamente el alcance sustentado.

============================================================
EVIDENCIA
============================================================

Cada elemento extraído debe incluir una cita literal y exacta del
TEXTO A ANALIZAR.

La cita debe sustentar la proposición completa que estás describiendo.

No uses como evidencia una frase que solamente:

- mencione el contexto;
- mencione una emoción;
- mencione una persona;
- mencione un acontecimiento;

si esa cita no sustenta realmente la acción o interferencia descrita.

No parafrasees dentro de evidence.quote.

============================================================
DEDUPLICACIÓN
============================================================

No generes múltiples elementos que representen esencialmente la misma
acción o la misma interferencia solo porque puedan describirse con
palabras diferentes.

Prefiere la representación mínima que conserve el significado relevante.

============================================================
CONTROL FINAL
============================================================

Antes de devolver cada candidate_action, comprueba:

1. ¿El usuario realmente realiza, intenta, planea, necesita, debe,
   posterga, evita o identifica esta conducta?
2. ¿La acción está sustentada por la evidencia citada?
3. ¿Estoy reconstruyendo una acción solo porque sería razonable en
   esa situación?
4. ¿Estoy inventando la conducta opuesta de una evitación?

Si 3 o 4 es SÍ, no extraigas esa acción.

Antes de devolver cada action_interference, comprueba:

1. ¿Existe una acción concreta identificable?
2. ¿La evidencia demuestra una dificultad u obstáculo respecto de esa
   acción?
3. ¿Estoy suponiendo interferencia únicamente porque existe una emoción
   o activación?
4. ¿Existe contraevidencia que indique que la acción se realiza
   normalmente?
5. ¿Estoy atribuyendo una causa emocional que este bloque no debe decidir?

Si la interferencia no está sustentada, no la extraigas.

Devuelve EXCLUSIVAMENTE el objeto JSON exigido por el schema.
No añadas texto fuera del JSON.
""".strip()