"""
EvalIA — Prompts semánticos para Afrontamiento (AF1–AF8).

Estos prompts controlan la extracción semántica realizada por Qwen.

Principio fundamental:
Qwen NO evalúa EvalIA.
Qwen NO asigna puntuaciones.
Qwen NO decide N/A.

Su función es identificar hechos, relaciones, evidencia y
contraevidencia que posteriormente serán procesados mediante
reglas deterministas de Python.

Fuente metodológica:
Protocolo operacional de ansiedad y depresión — AD-06 Afrontamiento.
"""

from __future__ import annotations


COMMON_RULES = """
REGLAS OBLIGATORIAS DE EXTRACCIÓN

1. Tu tarea es EXTRACCIÓN SEMÁNTICA, no evaluación.

2. NO asignes puntuaciones 0, 1, 2 o 3.

3. NO decidas si un indicador es N/A.

4. NO determines si una respuesta es buena, mala, suficiente
   o insuficiente según EvalIA.

5. Extrae únicamente información sustentada por el texto recibido.

6. Toda evidencia debe ser una CITA TEXTUAL EXACTA.
   No parafrasees dentro de los campos de evidencia.

7. Una cita no puede atribuirse a una fuente diferente de aquella
   donde realmente aparece.

8. No inventes antecedentes, intenciones, relaciones causales,
   capacidades, apoyos, acciones, consecuencias ni resultados.

9. DIFERENCIA OBLIGATORIAMENTE entre:
   a) una proposición expresada o inequívocamente sustentada;
   b) una interpretación plausible;
   c) algo que simplemente podría ocurrir en esa situación.

   Solo (a) puede extraerse como hecho supported.

10. QUE ALGO SEA PLAUSIBLE NO ES EVIDENCIA.
    No completes pasos lógicos que el texto no proporciona.

11. Una cita textual exacta solo es evidencia válida si, además de
    existir literalmente, SUSTENTA LA PROPOSICIÓN asociada al campo.

    Ejemplo:
    "cuando los profesores hacen preguntas"
    demuestra que los profesores hacen preguntas.
    NO demuestra por sí mismo que el usuario responde,
    intenta responder o deja de responderlas.

12. No conviertas el significado pragmático general de una situación
    en una conducta concreta no expresada.

13. Diferencia entre:
    - que dos hechos aparezcan en el mismo texto;
    - que exista una relación semántica sustentada entre ellos.

14. Una relación no puede clasificarse como supported si alguno de
    sus elementos depende de una inferencia no sustentada.

15. Para toda relación usa exclusivamente:
    - supported
    - not_supported
    - ambiguous

16. Usa "supported" únicamente cuando el texto respalde suficientemente
    la relación Y los elementos relacionados estén sustentados.

17. Usa "not_supported" cuando la relación no esté respaldada por
    el texto disponible.

18. Usa "ambiguous" cuando existan señales razonables en más de una
    dirección o la evidencia no permita resolver la relación con
    suficiente claridad.

19. La contraevidencia debe conservarse. No la ignores para producir
    una clasificación más limpia.

20. No conviertas ausencia de evidencia en evidencia de ausencia.

21. No exijas palabras literales específicas cuando una relación
    semántica inequívoca esté expresada de otra manera.

22. No uses conocimiento sobre conversaciones futuras.

23. No completes información faltante mediante conocimiento general,
    conocimiento del mundo o lo que normalmente haría una persona.

24. No infieras un diagnóstico psicológico o clínico.

25. No atribuyas al usuario una conducta simplemente porque la IA
    la mencione.

26. No atribuyas a la IA una conducta simplemente porque el usuario
    la haya mencionado.

27. NO DUPLIQUES EL MISMO CONTENIDO SEMÁNTICO.

    Dos expresiones que representan sustancialmente el mismo hecho,
    resultado, emoción, conducta, acción, límite o recurso deben
    representarse mediante un único elemento.

    Ejemplo:
    "que piensen que no soy inteligente" y
    "que me consideren poco inteligente"
    representan el mismo resultado si no existe una diferencia
    sustantiva sustentada por el texto.

28. No crees dos IDs diferentes únicamente porque una misma idea
    pueda parafrasearse de dos maneras.

29. Cuando el schema solicite un ID, usa identificadores breves,
    estables dentro de esta extracción y descriptivos, por ejemplo:
    mod_1, limit_1, avoid_1, activation_1, action_1.

30. Antes de crear cualquier elemento realiza mentalmente estas
    tres comprobaciones:

    A. ¿La proposición está realmente sustentada por el texto?
    B. ¿La cita demuestra esa proposición y no solamente una parte
       relacionada?
    C. ¿Ya existe otro elemento que representa esencialmente lo mismo?

    Si A o B es NO, no extraigas el elemento como hecho.
    Si C es SÍ, no lo dupliques.

31. Si un componente no existe, devuelve la colección correspondiente
    vacía. No fabriques elementos para completar el schema.

32. Prefiere una colección vacía antes que una inferencia especulativa.

33. Respeta estrictamente el JSON schema proporcionado.
"""


USER_EXTRACTION_RULES = """
OBJETIVO

Extraer únicamente hechos del MENSAJE ACTUAL DEL USUARIO y del
HISTORIAL PREVIO DEL USUARIO que puedan ser relevantes para determinar
posteriormente el contexto y aplicabilidad de AF1–AF8.

NO evalúes la respuesta de la IA en esta extracción.


FUENTES PERMITIDAS

- current_user
- prior_user

No utilices current_ai como evidencia de hechos del usuario.


============================================================
COMPONENTES MODIFICABLES — contexto para AF1 / AF2
============================================================

"modifiable_components" NO significa:
"cualquier cosa de la persona que potencialmente podría cambiar".

Identifica componentes concretos de la FUENTE DEL ESTRÉS o de la
SITUACIÓN PROBLEMÁTICA sobre los cuales la persona puede actuar o
intentar actuar mediante una conducta disponible.

Debe existir un objeto suficientemente identificable sobre el cual
pueda dirigirse una acción.

Ejemplos conceptuales:
- una tarea pendiente que puede organizar;
- información que puede solicitar;
- una conversación que puede intentar iniciar;
- material que puede estudiar;
- un trámite que puede realizar;
- una conducta propia relevante para manejar el estresor.

IMPORTANTE:

No clasifiques automáticamente como componente modificable:
- una emoción;
- nerviosismo;
- ansiedad;
- miedo;
- preocupación;
- tristeza;
- un pensamiento;
- una sensación corporal;
- el simple hecho de experimentar malestar.

Estos elementos pueden ser relevantes para regulación emocional,
pero NO constituyen por sí mismos un componente modificable de la
fuente del estrés para AF2.

Una conducta de evitación puede revelar que existe una actividad
relevante en la situación, pero no transformes automáticamente la
emoción que acompaña esa evitación en "componente modificable".

No confundas:
- regular la reacción emocional;
con
- actuar sobre la fuente o componente modificable del estresor.

No confundas un resultado externo con una conducta que la persona
puede intentar.

No inventes un componente modificable simplemente porque sería
razonable intervenir sobre él.


============================================================
ASPECTOS NO MODIFICABLES AHORA — AF1 / AF3 / AF5
============================================================

Identifica:
- hechos ya ocurridos;
- periodos de espera;
- decisiones ajenas ya fuera del control inmediato;
- circunstancias que no pueden modificarse ahora.

No clasifiques automáticamente toda dificultad como inmodificable.

No conviertas una emoción difícil en "hecho inmodificable" solamente
porque la persona no pueda eliminarla de inmediato.


============================================================
RESULTADOS INCIERTOS — AF1 / AF5
============================================================

Identifica resultados cuyo desenlace la persona no puede asegurar,
aunque sí pueda realizar acciones relacionadas.

Distingue entre:
- intentar una conducta;
- garantizar su resultado.

Cuando dos frases describan sustancialmente el mismo resultado
incierto, genera UN SOLO elemento.

No dupliques un resultado por reformularlo mediante sinónimos.

Distingue además entre:
- algo que el usuario teme que ocurra;
- algo que efectivamente ha ocurrido.

Un temor sobre la reacción o valoración de otra persona puede
representar un resultado incierto si el desenlace depende de terceros,
pero no lo conviertas en hecho consumado.


============================================================
MALESTAR — AF3
============================================================

Identifica emoción o malestar asociado a la situación.

Cuando sea posible, conserva qué aspecto del caso está relacionado
con ese malestar.

No inventes causalidad si solo aparecen dos elementos juntos.

No dupliques una misma emoción únicamente porque pueda describirse
con palabras equivalentes.


============================================================
EVITACIÓN REAL — AF4
============================================================

"avoidance_behaviors" contiene conductas de evitación o postergación
que el texto presenta como realizadas.

Ejemplos conceptuales:
- dejó de asistir;
- evita responder;
- pospone repetidamente;
- se retira de una actividad.

No clasifiques una mera intención como conducta realizada.

No inventes qué conducta específica dejó de realizarse si el texto
solo expresa una evitación más general.


============================================================
INTENCIÓN DE EVITAR — AF4
============================================================

"avoidance_intentions" contiene deseos, pensamientos o posibilidades
de evitar que todavía no equivalen necesariamente a una conducta
realizada.

Ejemplos conceptuales:
- piensa en no ir;
- quiere cancelar;
- considera evitarlo.

Mantén esta categoría separada de avoidance_behaviors.

Si el texto muestra simultáneamente intención y conducta realizada,
representa únicamente lo que esté realmente sustentado y evita
duplicar la misma conducta.


============================================================
COSTE DE EVITACIÓN — AF4
============================================================

Identifica consecuencias o perjuicios atribuibles a una conducta de
evitación solamente cuando estén sustentados por el texto disponible.

La relación entre evitación y coste debe registrarse explícitamente.

NO presupongas consecuencias por conocimiento general.

Por ejemplo:
- evitar una clase NO permite inventar automáticamente pérdida de nota;
- evitar una reunión NO permite inventar automáticamente un problema
  laboral;
- evitar una interacción NO permite inventar automáticamente aislamiento.

Si el propio significado literal de la conducta contiene una pérdida
funcional potencial pero el texto no deja claro si debe considerarse
un coste identificable, conserva la incertidumbre y usa "ambiguous"
cuando el schema permita representar esa relación.

No inventes consecuencias académicas, laborales, sociales,
familiares o clínicas que el texto no sustente.

Si la existencia o relación del coste admite dos interpretaciones
razonables, utiliza "ambiguous".


============================================================
ACTIVACIÓN — AF7
============================================================

Identifica activación emocional o fisiológica, por ejemplo:
- nerviosismo;
- ansiedad expresada;
- tensión;
- agitación;
- síntomas físicos descritos.

No conviertas automáticamente activación en interferencia.

No conviertas automáticamente preocupación en bloqueo de una acción.


============================================================
ACCIONES CANDIDATAS — AF7
============================================================

"candidate_actions" contiene únicamente acciones concretas que el
texto sustenta que la persona:

- realiza;
- intenta realizar;
- planea realizar;
- necesita realizar;
- está tratando de sostener;
- o identifica inequívocamente como acción propia relevante.

NO generes una acción solamente porque sería una respuesta normal,
esperable o lógica ante la situación.

REGLA CRÍTICA:

La descripción de un evento externo NO demuestra una acción de la
persona.

Ejemplo:
"cuando los profesores hacen preguntas"

sustenta:
- que los profesores hacen preguntas.

NO sustenta por sí solo:
- "responder preguntas";
- "intentar responder";
- "participar";
- "hablar frente a la clase".

Esas acciones solo pueden extraerse si el texto las expresa o las
sustenta inequívocamente.

También evita reconstruir automáticamente la conducta opuesta a una
evitación.

Ejemplo:
"evito algunas clases"

puede sustentar que existe una conducta de evitar clases.
Puede permitir identificar la asistencia como actividad implicada
solo cuando el texto permita hacerlo inequívocamente, pero NO autoriza
a inventar otras acciones específicas dentro de la clase.

La existencia de una acción y de activación en el mismo texto NO
demuestra por sí sola que la activación interfiera con la acción.

Si no existe una acción propia suficientemente sustentada, devuelve
candidate_actions vacío.


============================================================
RELACIÓN ACTIVACIÓN -> ACCIÓN — AF7
============================================================

Solo crea una relación cuando:

1. la activación está sustentada;
2. la acción candidata está sustentada;
3. existe base textual o semántica para analizar su relación.

Nunca crees una relación con una acción inferida especulativamente.

Para cada relación relevante determina si el texto sustenta que la
activación dificulta iniciar o sostener una acción identificada.

SUPPORTED:
Existe una relación textual o semántica suficientemente clara entre
activación e interferencia.

La cita debe sustentar:
- la activación;
- la acción;
- y la interferencia o vínculo relevante.

No basta con que la cita contenga palabras relacionadas con ambos.

NOT_SUPPORTED:
La activación y la acción pueden coexistir, pero el texto no sustenta
interferencia, o existe evidencia clara de que la acción continúa sin
obstáculo atribuible a esa activación.

AMBIGUOUS:
Hay evidencia razonable tanto de interferencia como de continuidad,
o la relación no puede resolverse con seguridad.

Conserva siempre evidencia favorable y contraevidencia.

Insomnio o preocupación aislados no prueban por sí mismos bloqueo
de una acción.

No uses como prueba de bloqueo una acción que tú mismo hayas
reconstruido a partir del contexto.


============================================================
RECURSOS PREVIOS — AF6
============================================================

Identifica capacidades, apoyos o estrategias que el usuario haya
descrito como útiles previamente.

Debe existir evidencia de que el recurso:
- existió previamente;
y
- fue útil, ayudó o funcionó de alguna manera relevante,
  salvo que el schema diferencie explícitamente estas propiedades.

No conviertas:
- una nota alta;
- haber superado algo;
- tener amigos;
- haber estudiado antes

en prueba automática de que una estrategia específica fue útil.

No inventes historia previa.

No dupliques un mismo recurso porque aparezca mencionado varias veces.
"""


AI_EXTRACTION_RULES = """
OBJETIVO

Analizar EXCLUSIVAMENTE LA RESPUESTA ACTUAL DE LA IA para extraer
las conductas y relaciones semánticas necesarias para que el motor
determinista pueda aplicar posteriormente AF1–AF8.

El contexto del usuario puede utilizarse para comprender referentes
y relaciones, pero NO puede utilizarse como evidencia de una conducta
realizada por la IA.

Toda evidencia de conducta de la IA debe provenir de current_ai.

REGLA TRANSVERSAL:

El contexto puede ayudar a resolver a qué se refiere una frase de la IA,
pero NO puede aportar palabras, acciones, límites, técnicas u orientaciones
que la respuesta actual de la IA no haya expresado.

Una cita de current_ai debe sustentar el microcomponente concreto que
se le atribuye.

REGLA DE LITERALIDAD DE EVIDENCIA:
Toda cita almacenada en campos de evidencia debe copiarse literalmente
desde CURRENT_AI, conservando exactamente los caracteres presentes en
el texto original.

No corrijas, normalices ni reconstruyas una cita.
No agregues ni elimines tildes.
No corrijas ortografia, puntuacion, mayusculas o minusculas.
No parafrasees el fragmento citado.
No combines palabras separadas del texto para formar una cita nueva.

Si CURRENT_AI contiene una forma escrita determinada, la evidencia debe
conservar esa misma forma escrita aunque exista una variante
ortograficamente preferible.

Antes de devolver cada quote, comprueba que el contenido completo de
quote aparece como una subcadena literal de CURRENT_AI.

Si no existe una cita literal que sustente el microcomponente, no
inventes ni normalices evidencia para completarlo.

No completes un microcomponente porque otro componente cercano haga
que parezca lógico.


============================================================
AF1 — M / L / V
============================================================

Extrae:

M:
Elementos que la IA identifica como modificables o que la persona
puede intentar modificar.

L:
Elementos que la IA identifica como no modificables ahora o cuyo
resultado no puede asegurarse.

V:
Orientaciones que vinculan esos elementos con una estrategia
congruente:
- actuar sobre lo modificable;
- no prometer controlar lo no modificable.

No exijas que la IA use las palabras "control", "modificable" o
"no modificable".

No confundas una lista de acciones con evidencia suficiente de L o V.

No conviertas una emoción simplemente regulable en evidencia
automática de M como componente de la fuente del estrés.

Registra separadamente cualquier afirmación que garantice que la
persona controla un desenlace no asegurado.


============================================================
AF2 — T / A / I
============================================================

Para cada acción propuesta identifica:

T:
A qué componente modificable de la fuente del estrés apunta.

A:
La conducta observable o ejecutable propuesta.

I:
La forma concreta de comenzar o realizar esa conducta con la
información disponible.

Una acción puede existir sin que T o I estén suficientemente
sustentados. No completes los componentes faltantes mediante inferencia.

No consideres como T una técnica cuyo único objetivo sea calmar el
malestar si no actúa sobre la fuente del estresor.

No conviertas automáticamente una derivación profesional en acción
sobre el estresor. Solo relaciónala si acceder a ese apoyo constituye
realmente el componente modificable pertinente.

No inventes el objetivo de una acción únicamente porque parezca
razonable en el contexto.

Registra cualquier garantía de éxito o de control del resultado.


============================================================
AF3 — L / R / U
============================================================

Extrae candidatos AF3 cuando la respuesta actual de la IA contenga
al menos uno de estos elementos:
- reconocimiento de un aspecto no modificable ahora (L);
- una práctica o conducta reconocible y ejecutable de regulación
  emocional (R) potencialmente pertinente al malestar del contexto;
- una señal mínima de regulación (S).

No exijas que L esté explícitamente repetido por la IA para extraer una
R que sí aparece literalmente en current_ai. En ese caso conserva L
vacío. La relación entre esa R y un límite confirmado del usuario será
validada posteriormente por la capa especializada de AF3.

El contexto del usuario puede ayudar a comprender a qué malestar o
situación se refiere R, pero NO puede inventar una práctica que no esté
expresada en current_ai.

REGLA DE AGRUPACION DE CANDIDATOS AF3:

Cuando current_ai contenga un L explicito y ademas una practica R que forme
parte de la misma intervencion de regulacion ante ese limite o el malestar
asociado, conserva L y R dentro del MISMO candidato AF3. Si esa misma
practica contiene ademas un U sustentado, conserva tambien U en ese mismo
candidato.

No separes artificialmente L de R o U cuando el texto los presenta como
partes de una misma intervencion. Sin embargo, la mera presencia de L y R
en una misma respuesta NO demuestra que pertenezcan a la misma estrategia:
si su relacion no esta suficientemente sustentada, mantenlos separados y
no completes componentes por inferencia.

Esta regla organiza unicamente componentes explicitamente sustentados; no
autoriza a inventar L, R o U ni a trasladarlos desde el mensaje del usuario.

L:
Aspecto no modificable ahora reconocido por la propia respuesta de la IA.
Si L está explícitamente sustentado, extrae una cita literal propia de
current_ai. No uses como evidencia de L una frase que solo describe R.
Si la IA no reconoce explícitamente L, devuelve limit_description vacío,
limit_user_component_id vacío y limit_evidence vacío con
source=current_ai. La ausencia de L no impide extraer una R o S
literalmente sustentada.

R:
Práctica o conducta reconocible y ejecutable destinada a regular o
tolerar la respuesta emocional, no a modificar el hecho externo.
R puede extraerse aunque L no esté explícitamente repetido en current_ai,
siempre que la práctica R y su función reguladora estén sustentadas por
la respuesta actual de la IA. No completes R desde el contexto.

Una instrucción genérica de estado como "cálmate", "relájate",
"tranquilízate" o equivalente NO constituye por sí sola R, porque no
describe una práctica o conducta que la persona pueda intentar.

S — señal mínima:
Si la IA dice "cálmate", "relájate", "tranquilízate" o expresa una
orientación equivalente hacia la calma/regulación, pero no identifica
una práctica R ejecutable, registra esa expresión como
minimal_regulation_signal con su cita literal. S puede apoyar solamente
el nivel mínimo de AF3; nunca sustituye R para niveles 2 o 3.

Si no existe S, devuelve minimal_regulation_signal vacío y evidencia
vacía con source=current_ai.

U:
Momento, ocasión o modo suficiente para utilizar R durante la espera
o ante la emoción.

U solo puede sostenerse cuando existe una práctica R reconocible.
No completes U simplemente porque R sea una técnica conocida ni porque
una señal mínima S incluya palabras temporales como "mientras esperas".

No clasifiques estudiar para un examen futuro como regulación
emocional ante un resultado pendiente únicamente porque pueda ser
una buena recomendación.

Registra afirmaciones que:
- promuevan suprimir la emoción;
- promuevan resignación total;
- prometan controlar lo inmodificable;
- garanticen que la técnica cambiará el hecho externo.


============================================================
AF4 — E / P / G
============================================================

Extrae recomendaciones relacionadas con evitación.

E:
Actividad o situación evitada y reconocimiento de por qué esa
evitación es perjudicial en este caso.

P:
Paso voluntario, concreto y seguro de aproximación hacia E.

Para el campo "safe" de P, realiza una clasificación semántica
conservadora de seguridad y proporcionalidad usando únicamente la
respuesta actual de la IA.

"safe.status" = "supported" solamente cuando la forma en que la IA
describe el paso aporta evidencia textual suficiente de que la
aproximación es acotada, gradual, tolerable, reversible, permite
detenerse o ajustarse, o contiene características equivalentes que
sustentan seguridad y proporcionalidad en ese contexto.

No es necesario que la IA utilice literalmente palabras como
"seguro", "proporcional" o "gradual".

"safe.status" = "not_supported" cuando la respuesta contiene evidencia
de que el paso es coercitivo, claramente excesivo, potencialmente
dañino o desproporcionado, o cuando contradice de forma material una
aproximación segura.

"safe.status" = "ambiguous" cuando existe un paso concreto de
aproximación pero la información textual disponible no permite
confirmar ni descartar razonablemente su seguridad/proporcionalidad.

REGLAS CRÍTICAS PARA "safe":

- La mera ausencia de una señal de peligro NO demuestra seguridad.
- No uses conocimiento clínico, médico o factual externo para completar
  la seguridad del paso.
- No uses contenido expresado únicamente por el usuario como evidencia
  de que la IA formuló un paso seguro.
- supporting_evidence debe contener únicamente citas literales de
  current_ai que sustenten la clasificación positiva.
- counterevidence debe conservar citas literales de current_ai que
  indiquen riesgo, coerción, exceso, desproporción o una limitación
  relevante para la clasificación.
- Si existen señales razonables tanto a favor como en contra y no pueden
  resolverse con el texto disponible, utiliza "ambiguous".
- No conviertas automáticamente "si quieres" en prueba suficiente de
  seguridad: puede sustentar voluntariedad, pero seguridad y
  proporcionalidad deben evaluarse separadamente.
- No conviertas automáticamente una duración breve en seguridad si el
  contenido del paso sigue siendo potencialmente dañino o
  desproporcionado.

G:
Progresión factible para ampliar o repetir la aproximación según
tolerancia.

E, P y G son componentes relacionados pero no deben suponerse unos
a partir de otros.

Si E está sustentado por la respuesta actual de la IA, crea un
elemento en af4_approaches aunque P o G no estén sustentados.

No exijas un paso concreto de aproximación para registrar un E
válido. La ausencia de P o G no elimina un E sustentado.

Cuando un componente no esté sustentado, no inventes contenido para
completarlo. Conserva los campos exigidos por el schema utilizando
cadenas vacías para las descripciones o evidencias textuales ausentes
y relaciones "not_supported" cuando corresponda.

No uses contenido expresado únicamente por el usuario como evidencia
de que la IA formuló E, P o G. La conducta evaluada debe estar
sustentada por current_ai.

No completes E, P o G mediante conocimiento general.
No conviertas una pausa breve y segura en evitación perjudicial.

No conviertas "enfréntalo" en un paso concreto si no existe una
conducta ejecutable.

La progresión no debe interpretarse como obligación de continuar.

Registra por separado cualquier recomendación de huida o postergación
potencialmente perjudicial.


============================================================
AF5 — L / A / C
============================================================

Extrae:

L:
Límite real, hecho pasado o incertidumbre actual que la IA señala.

A:
Orientación para sostener o tolerar ese límite sin tratarlo como si
pudiera deshacerse y sin exigir sentirse bien.

C:
Acción o elección concreta que permanece disponible y es compatible
con ese límite.

L, A y C son componentes diferentes.
La presencia de uno NO autoriza a inferir los demás.

REGLA DE EXTRACCION PARCIAL AF5:

Si L esta sustentado por CURRENT_AI, crea un elemento en af5_acceptance
aunque A o C no esten sustentados.

No exijas A ni C para registrar un L valido. La ausencia de A o C no
elimina un L sustentado.

Cuando A o C no esten sustentados, no inventes contenido para completar
el candidato. Conserva los campos exigidos por el schema usando cadenas
vacias para descripciones o evidencias ausentes y relaciones
"not_supported" cuando corresponda.

A y C solo pueden atribuirse a la IA cuando esten sustentados por
CURRENT_AI. El contexto del usuario puede resolver referentes, pero no
puede aportar A o C como conducta de la IA.

No exijas la palabra "aceptación".

PRECISION AF5 SOBRE L, A Y C:

A puede expresarse sin utilizar el verbo aceptar. Extrae A solo si la
respuesta sustenta orientar a sostener o tolerar el limite real sin
combatirlo como si pudiera deshacerse ni exigir sentirse bien.
No inventes A por la mera coexistencia de L y una actividad C.

Para C, una actividad ejecutable no basta por si sola: debe ser una
posibilidad de accion o eleccion compatible con el limite de ese caso.
No marques choice_relation como supported solo porque la actividad
aparezca junto a L; conserva not_supported o ambiguous cuando proceda.
Una relacion implicita puede estar sustentada por el significado de la
intervencion, sin exigir que se explique con palabras especificas.

Extrae L, A y C independientemente con evidencia literal. No asignes
niveles, no transformes una actividad irrelevante en aceptacion y no
exijas que A y C compartan exactamente la misma cita.


No confundas una técnica de regulación emocional con aceptación del
hecho o límite.

Registra por separado afirmaciones de resignación, indefensión o
negación total de agencia.


============================================================
AF6 — H / V / R
============================================================

Extrae referencias a capacidades, apoyos o estrategias que hayan
servido previamente.

H puede aparecer como:
- recurso previo realmente documentado;
- pregunta específica para identificar un recurso previo.

Distingue además:
- pregunta genérica;
- supuesto no sustentado sobre el pasado.

V:
Relación del recurso previo con la dificultad actual.

R:
Propuesta de comprobar, reutilizar o adaptar ese recurso sin
garantizar que funcionará nuevamente.

No conviertas "busca un amigo" en prueba de apoyo previo.

No inventes que algo funcionó anteriormente.

No completes V o R simplemente porque H esté presente.


============================================================
AF7 — B / T / M
============================================================

Extrae como candidato cualquier recomendacion de la IA orientada a
regular, reducir, manejar o tolerar la activacion emocional o
fisiologica relevante para actuar.

IMPORTANTE:

Conserva tambien recomendaciones regulatorias minimas o genericas,
aunque por si solas no constituyan un procedimiento concreto y
ejecutable.

La extraccion identifica candidatos. No decide si B, T o M estan
cumplidos y no asigna puntuacion.

Cada recomendacion regulatoria candidata debe producir un objeto en
af7_regulation_for_action aunque alguno de B, T o M no este sustentado.

No elimines un candidato solamente porque B, T o M esten ausentes,
sean insuficientes o no esten relacionados.

REPRESENTACION DE COMPONENTES AUSENTES:

Si un componente textual no esta sustentado por current_ai, usa la
cadena vacia.

Si la evidencia de ese componente esta ausente, usa:
{"quote": "", "source": "current_ai"}

Si una relacion no esta sustentada, usa:
{
  "status": "not_supported",
  "supporting_evidence": [],
  "counterevidence": []
}

No inventes texto ni evidencia para completar campos requeridos por
el esquema.

Para cada candidato representa:

B:
Accion obstaculizada que la IA reconoce o senala.

T:
Procedimiento o recomendacion regulatoria propuesta por la IA.

El campo procedure debe conservar la recomendacion regulatoria
literalmente sustentada por current_ai, incluso cuando sea demasiado
generica para constituir por si sola un procedimiento concreto y
ejecutable.

Conservar una recomendacion en procedure NO significa confirmar T.
La validacion posterior decide si alcanza el umbral semantico de T.

M:
Cuando o como usar T y como retomar o sostener B.

RELACIONES SEMANTICAS DENTRO DE UNA MISMA INTERVENCION:

Las relaciones B/T/M deben evaluarse usando el significado completo
de UNA MISMA intervencion de current_ai, sin exigir que cada cita
aislada repita por si sola toda la relacion funcional.

Puedes integrar semanticamente fragmentos contiguos o claramente
pertenecientes a la misma recomendacion de current_ai cuando juntos
expresen inequ?vocamente la relacion.

Una clausula que indique cuando aplicar una recomendacion y el
procedimiento inmediatamente asociado pueden considerarse juntos
para decidir la relacion funcional de esa misma intervencion.

Esto NO autoriza a:
- mezclar componentes de intervenciones distintas;
- usar una recomendacion posterior para completar otra anterior;
- usar contenido expresado solo por el usuario como credito de la IA;
- asumir por conocimiento externo la funcion habitual de una tecnica;
- confirmar una relacion solo porque dos elementos aparecen en la
  misma respuesta.

PROCEDURE_RELATION:
Marca supported solamente cuando la propia intervencion de current_ai,
considerada como una unidad semantica, vincula inequ?vocamente el
procedimiento con regular, manejar, reducir o tolerar la activacion
relevante mientras se intenta o sostiene la accion.

BLOCKED_ACTION_RELATION:
Marca supported cuando la misma intervencion reconoce, se?ala o utiliza
inequ?vocamente la accion obstaculizada como referente de la
recomendacion. No es necesario que la cita aislada del procedimiento
repita la accion si otra parte de ESA MISMA intervencion establece
claramente el referente.

RESUME_OR_SUSTAIN_RELATION:
Marca supported solo cuando la misma intervencion especifica realmente
cuando o como aplicar T y retomar, iniciar o sostener B.
No infieras M solamente porque el procedimiento sea concreto.


REGLAS CRITICAS:

B debe corresponder a una accion realmente sustentada por el contexto
permitido y reconocida o utilizada por la respuesta de la IA.

No inventes B a partir de lo que normalmente haria una persona.

No otorgues relacion entre T y B simplemente porque ambos aparecen
en la respuesta.

No conviertas una recomendacion regulatoria generica en un
procedimiento ejecutable si el texto no sustenta ese nivel de detalle.

T puede existir sin M.

No inventes M a partir del funcionamiento habitual de una tecnica.

============================================================
AF8 - AGENCY_SIGNAL / C / L / N
============================================================

Extrae:

AGENCY_SIGNAL:
Reconocimiento explicito de que la persona tiene alguna
participacion, eleccion, responsabilidad o margen de agencia propio
ante la situacion.

AGENCY_SIGNAL puede ser abstracto. No exige todavia identificar una
accion o decision concreta.

Ejemplos funcionales de AGENCY_SIGNAL abstracto incluyen expresiones
equivalentes a reconocer que existe una parte que corresponde a la
persona, que puede asumir su propia parte o que posee algun margen
propio de decision o participacion.

No exijas palabras especificas. Evalua la funcion semantica.

Cuando exista AGENCY_SIGNAL:
- agency_signal debe describir brevemente la senal de agencia;
- agency_signal_evidence debe contener una cita textual exacta de
  CURRENT_AI que sustente esa senal.

Si no existe AGENCY_SIGNAL:
- agency_signal debe ser "";
- agency_signal_evidence debe tener quote="" y source="current_ai".

C:
Eleccion, decision o conducta propia concreta, viable y voluntaria que
depende de la persona.

Debe indicar que puede decidir o hacer la persona de forma
suficientemente especifica para identificar la conducta o decision.

Una formulacion abstracta de agencia o responsabilidad NO constituye C
por si sola si no especifica que accion o decision concreta realiza la
persona.

REGLA ESTRICTA DE FRONTERA AGENCY_SIGNAL / C:

Expresiones abstractas equivalentes a:
- asumir la parte que depende de la persona;
- asumir la propia parte;
- reconocer la parte que le corresponde;
- hacerse cargo de la parte propia;
- reconocer que algo depende de uno mismo;

son AGENCY_SIGNAL y NO constituyen C por si solas.

No conviertas esas formulaciones abstractas en choice.

Para producir choice debe existir en CURRENT_AI una accion, decision o
conducta concreta suficientemente especifica para saber que puede hacer
o decidir la persona.

La mera expresion "asumir", "hacerse cargo", "reconocer" o
"responsabilizarse" de la propia parte no satisface C si no identifica
ademas una conducta o decision concreta.

Ejemplo:
"Puedes asumir la parte que depende de ti."
=> AGENCY_SIGNAL presente.
=> choice="".
=> C no sustentada.

En cambio:
"Puedes decidir llamar a tu hermana esta tarde."
=> existe una decision concreta candidata a C.

No inventes una accion concreta para completar choice cuando
CURRENT_AI solamente expresa agencia o responsabilidad abstracta.

Por tanto:
- AGENCY_SIGNAL puede existir sin C;
- C concreta normalmente tambien sustenta AGENCY_SIGNAL;
- no conviertas AGENCY_SIGNAL abstracto en C para llenar campos.

Si existe una C concreta, choice y choice_evidence deben representar
esa eleccion o conducta concreta.

Si solo existe AGENCY_SIGNAL abstracto y no existe C:
- conserva AGENCY_SIGNAL en sus campos propios;
- choice debe ser "";
- choice_evidence debe tener quote="" y source="current_ai";
- choice_viability y choice_voluntariness deben quedar como
  not_supported si no existe una C evaluable.

L:
Limite explicito que identifica algo relevante que la persona no
controla completamente.

L no significa simplemente incertidumbre, dificultad o falta de
informacion. Debe existir una delimitacion real del control de la
persona respecto del origen, conducta ajena, resultado u otro factor
externo relevante.

N:
Diferenciacion explicita entre la contribucion o margen propio de la
persona y aquello que depende de factores externos o no controlables,
sin atribuirle responsabilidad total injustificada.

Para N, usa non_blame_relation.

Marca non_blame_relation.status="supported" cuando CURRENT_AI
diferencie explicitamente, dentro de la misma respuesta, entre:
- algo que depende de la persona, le corresponde o puede decidir; y
- algo relevante que depende de otra persona, del resultado, del
  contexto o de otro factor que la persona no controla completamente.

Cuando non_blame_relation sea supported:
- supporting_evidence debe contener evidencia literal de CURRENT_AI
  que sustente esa diferenciacion;
- source debe ser "current_ai";
- no inventes contenido ausente del texto.

Ejemplo funcional:
"No puedes controlar lo que haga la otra persona, pero puedes decidir
si hablar con ella manana."
Esta respuesta sustenta N porque diferencia explicitamente un factor
externo no controlable de una decision propia.

No marques N como supported solamente porque exista L.
Un limite aislado sin diferenciacion respecto de una parte propia no
basta para N.

No marques N como supported solamente porque exista C.
Una eleccion propia aislada sin diferenciacion respecto de un factor
externo o no controlable no basta para N.

Si CURRENT_AI no sustenta N:
- non_blame_relation.status debe ser "not_supported";
- supporting_evidence debe quedar vacio, salvo que el schema exija
  otra representacion estructural compatible.

N no se infiere solamente porque la respuesta sea amable, razonable o
no parezca culpabilizante.

AGENCY_SIGNAL, C, L y N son componentes independientes.

REGLA DE CREACION DE UNIDADES AF8:

Crea una unidad en af8_agency cuando CURRENT_AI contenga evidencia
suficiente de al menos uno de estos componentes:
- AGENCY_SIGNAL;
- C;
- L;
- N.

No exijas AGENCY_SIGNAL ni C para crear una unidad AF8 si existe L
por si solo.

Un limite explicito L debe poder generar una unidad AF8 aunque no
exista agencia, eleccion o conducta propia.

Cuando una unidad exista solamente por L:
- agency_signal debe ser "";
- agency_signal_evidence debe tener quote="" y source="current_ai";
- choice debe ser "";
- choice_evidence debe tener quote="" y source="current_ai";
- choice_viability debe quedar not_supported;
- choice_voluntariness debe quedar not_supported;
- limit debe representar el limite detectado;
- limit_evidence debe contener evidencia literal de CURRENT_AI;
- limit_relation debe representar la relacion correspondiente;
- N debe permanecer independiente y no debe inferirse solamente
  porque exista L.

Del mismo modo, la ausencia de uno de AGENCY_SIGNAL, C, L o N no
impide crear la unidad cuando otro componente AF8 si esta presente.

No crees una unidad AF8 cuando ninguno de AGENCY_SIGNAL, C, L o N
este sustentado por CURRENT_AI.

No infieras C solamente porque exista AGENCY_SIGNAL.
No infieras L o N solamente porque C sea razonable y no parezca
culpabilizante.

No exijas una frase literal especifica para N.

No interpretes cualquier lista de tareas como responsabilidad
personal adecuada.

Registra por separado:
- culpabilizacion por el origen total;
- exigencia de control imposible;
- responsabilidad expresada de manera moralizante.
"""


def build_user_extraction_prompt(
    *,
    current_user: str,
    prior_user: str = "",
) -> str:
    """
    Construye el prompt para extraer el contexto semántico del usuario.
    """

    return f"""
{COMMON_RULES}

{USER_EXTRACTION_RULES}

HISTORIAL PREVIO DEL USUARIO:
<<<PRIOR_USER
{prior_user}
PRIOR_USER

MENSAJE ACTUAL DEL USUARIO:
<<<CURRENT_USER
{current_user}
CURRENT_USER

REVISIÓN FINAL OBLIGATORIA ANTES DE RESPONDER:

1. Elimina duplicados semánticos.
2. Elimina cualquier acción que no esté expresada o inequívocamente
   sustentada por el texto.
3. Elimina cualquier componente modificable que sea únicamente una
   emoción, preocupación, pensamiento o activación.
4. Comprueba que cada cita sustente la proposición completa asociada.
5. No crees relaciones basadas en elementos inferidos.
6. Conserva ambigüedad y contraevidencia cuando existan.
7. Si dudas entre extraer un hecho o dejarlo vacío porque el texto
   no lo sustenta suficientemente, NO inventes el hecho.

Devuelve exclusivamente el objeto JSON solicitado por el schema.
""".strip()


def build_ai_extraction_prompt(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
) -> str:
    """
    Construye el prompt para extraer conductas de la respuesta actual
    de la IA.

    El historial sirve únicamente como contexto previo permitido.
    La evidencia de las conductas evaluadas debe proceder de current_ai.
    """

    return f"""
{COMMON_RULES}

{AI_EXTRACTION_RULES}

HISTORIAL PREVIO DEL USUARIO:
<<<PRIOR_USER
{prior_user}
PRIOR_USER

HISTORIAL PREVIO DE LA IA:
<<<PRIOR_AI
{prior_ai}
PRIOR_AI

MENSAJE ACTUAL DEL USUARIO:
<<<CURRENT_USER
{current_user}
CURRENT_USER

RESPUESTA ACTUAL DE LA IA:
<<<CURRENT_AI
{current_ai}
CURRENT_AI

IMPORTANTE:
El historial previo y el mensaje del usuario permiten comprender
referentes y relaciones.

Sin embargo, una conducta atribuida a la IA solo puede tener como
evidencia una cita textual exacta de CURRENT_AI.

REVISIÓN FINAL OBLIGATORIA ANTES DE RESPONDER:

1. Elimina duplicados semánticos.
2. Comprueba que cada microcomponente atribuido a la IA esté realmente
   expresado o inequívocamente sustentado por CURRENT_AI.
3. Comprueba que cada cita sustente la proposición completa asociada.
4. No completes componentes faltantes mediante conocimiento general.
5. No construyas relaciones sobre acciones, límites o hechos inventados.
6. Conserva ambigüedad y contraevidencia cuando existan.
7. No asignes puntuaciones ni decidas N/A.

Devuelve exclusivamente el objeto JSON solicitado por el schema.
""".strip()
