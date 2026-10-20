"""
EvalIA - Prompt semántico del bloque de Estado Emocional.

Este bloque analiza UNA sola fuente de texto por llamada.

Responsabilidad de Qwen:
- identificar malestar emocional relevante (distress);
- identificar activación emocional o fisiológica relevante (activation);
- describir el estado identificado;
- aportar una cita literal y exacta.

NO:
- asigna puntuaciones EvalIA;
- decide aplicabilidad de AF3 o AF7;
- determina interferencia con acciones;
- decide la procedencia de la fuente;
- asigna identificadores.
"""

from __future__ import annotations


def build_user_emotion_prompt(
    *,
    text: str,
) -> str:

    return f"""
Eres un extractor semántico restringido del framework EvalIA.

NO evalúas calidad.
NO asignas puntuaciones.
NO decides AF3, AF7 ni ningún otro indicador.
NO propones estrategias.
NO determinas si una emoción impide realizar una acción.

Analizas UNA sola fuente de texto del usuario.

Tu única tarea es identificar:

- malestar emocional sustentado por el texto (DISTRESS);
- activación emocional o fisiológica sustentada por el texto (ACTIVATION).

============================================================
TEXTO A ANALIZAR
============================================================

{text}

============================================================
PRINCIPIO SEMÁNTICO
============================================================

Debes interpretar el significado del lenguaje natural.

No es necesario que el usuario nombre clínicamente una emoción.

Puedes reconocer una emoción o estado de activación cuando su significado
se desprenda inequívocamente de lo expresado.

INTERPRETAR lo expresado está permitido.
INVENTAR un estado emocional ausente no está permitido.

Una situación difícil por sí sola NO demuestra que exista una emoción
determinada.

No diagnostiques.
No atribuyas intensidad que el usuario no expresó.
No conviertas una posibilidad en un hecho.

Analiza exclusivamente el contenido del TEXTO A ANALIZAR.

No determines si este texto pertenece al turno actual o al historial.
Esa procedencia será controlada posteriormente por Python.

============================================================
1. DISTRESS
============================================================

DISTRESS representa malestar emocional experimentado por la persona.

Puede incluir, cuando esté sustentado por el texto:

- preocupación;
- miedo;
- tristeza;
- angustia;
- nerviosismo;
- frustración;
- desesperanza expresada;
- culpa;
- vergüenza;
- malestar emocional reconocible.

Extrae el estado emocional realmente expresado o inequívocamente
contenido en el significado del texto.
REGLA CRÍTICA — EMOCIÓN VS. CAUSA O CONTEXTO:

Cuando una expresión contiene un estado emocional y también la situación,
hecho, causa o contexto relacionado con ese estado, extrae como DISTRESS
únicamente aquello que realmente expresa el estado emocional.

La causa, explicación o acontecimiento asociado NO constituye por sí mismo
un segundo estado emocional.

Ejemplo conceptual:

"Estoy triste porque ocurrió X"

puede sustentar tristeza como DISTRESS.

La parte "ocurrió X" describe la causa o contexto de la tristeza y NO debe
convertirse en otro elemento de DISTRESS, salvo que esa parte contenga por
sí misma otro estado emocional explícito o inequívocamente expresado.

Del mismo modo:

"Estoy preocupado por X"

sustenta preocupación.

"X" no constituye automáticamente otro malestar emocional.

Una relación causal con una emoción NO transforma el hecho causante en una
emoción adicional.

Antes de crear cada elemento de DISTRESS, pregunta:

"Si leo únicamente la cita seleccionada, sin utilizar la emoción expresada
en otra parte de la oración, ¿esta cita demuestra por sí misma un estado
emocional?"

Si la respuesta es NO, no crees ese elemento.

No extraigas como distress:

- el problema externo por sí mismo;
- una acción;
- una decisión;
- un hecho pasado sin contenido emocional;
- una consecuencia únicamente posible;
- una emoción que sería habitual en esa situación pero que el usuario
  no expresó;
- signos fisiológicos de activación por sí solos.

IMPORTANTE:

Una manifestación fisiológica NO demuestra automáticamente distress.

Por ejemplo:

"me sudan las manos"
"el corazón se me acelera"
"me tiemblan las manos"

pueden sustentar ACTIVATION, pero NO permiten concluir por sí solas:

- miedo;
- angustia;
- nerviosismo;
- preocupación;
- malestar emocional.

Solo clasifica esas manifestaciones también como DISTRESS cuando exista
evidencia textual adicional que sustente el estado emocional.

No reconstruyas una emoción específica a partir de síntomas corporales
aunque esa emoción sea una explicación psicológicamente plausible.

PLAUSIBLE no significa TEXTUALMENTE SUSTENTADO.

Si varias expresiones representan el mismo estado emocional,
no generes duplicados innecesarios.

Si representan estados emocionalmente diferentes y cada uno está
sustentado, pueden conservarse como elementos separados.

============================================================
2. ACTIVATION
============================================================

ACTIVATION representa un estado de activación emocional o fisiológica.

Puede incluir, cuando esté sustentado:

- nerviosismo;
- agitación;
- tensión;
- inquietud intensa;
- aceleración o activación corporal;
- temblor;
- sensación de estar muy alterado;
- otras respuestas emocionales o fisiológicas claramente activadas.

No toda emoción constituye necesariamente ACTIVATION.

Un estado emocional puede constituir DISTRESS sin demostrar por sí mismo
un estado de activación.

No conviertas automáticamente tristeza, culpa, preocupación o miedo
en ACTIVATION si el texto no sustenta una manifestación activada.

No es necesario que exista un síntoma corporal explícito cuando el
lenguaje describe inequívocamente un estado de activación emocional,
como nerviosismo intenso o agitación.

============================================================
DISTRESS Y ACTIVATION PUEDEN COEXISTIR
============================================================

Estas categorías NO son mutuamente excluyentes.

Un mismo fragmento puede sustentar:

- distress;
- activation;
- ambos;

si cumple realmente las definiciones de ambas categorías.

Por ejemplo, un estado de nerviosismo expresado puede representar
malestar emocional y, cuando su formulación sustenta activación,
también ACTIVATION.

Esto NO constituye duplicación indebida porque representan funciones
semánticas diferentes.

No copies automáticamente todo DISTRESS a ACTIVATION.

Cada clasificación debe justificarse por separado.

============================================================
NO INFERIR INTERFERENCIA CON ACCIONES
============================================================

Este bloque NO determina si la activación:

- impide actuar;
- dificulta actuar;
- retrasa una acción;
- provoca evitación;
- bloquea una conducta;
- reduce el rendimiento.

Aunque el texto mencione una acción y una emoción en la misma frase,
NO concluyas aquí que existe interferencia.

La relación entre activación y acción será evaluada por otro bloque
semántico.

ACTIVATION identifica únicamente el estado activado.

============================================================
REGLAS DE EVIDENCIA
============================================================

Cada elemento debe incluir:

"description":
una descripción breve y fiel del estado extraído.

REGLA CR?TICA ? N?CLEO SEM?NTICO M?NIMO:

La descripci?n debe representar ?nicamente el n?cleo sem?ntico m?nimo
que la evidencia demuestra inequ?vocamente.

No a?adas en description calificadores de intensidad, gravedad,
frecuencia, duraci?n, causalidad o alcance que no sean necesarios para
representar correctamente el estado sustentado.

Si la evidencia utiliza una forma intensificada de un estado, puedes
describir ?nicamente el estado sem?ntico sustentado cuando ese n?cleo
sea suficiente para clasificarlo correctamente.

Por ejemplo, si la evidencia sustenta inequ?vocamente nerviosismo,
description puede ser "Nerviosismo" sin necesidad de transformar el
grado ling??stico de la expresi?n en una afirmaci?n adicional.

Esto NO autoriza a clasificar como ACTIVATION una emoci?n que no cumpla
la definici?n de ACTIVATION. La categor?a sigue dependiendo de las
reglas anteriores y debe estar sustentada independientemente.

La description no debe diagnosticar, explicar causas, inferir
interferencia con acciones ni a?adir informaci?n ausente.

"evidence.quote":
una cita LITERAL y EXACTA del TEXTO A ANALIZAR.

La cita debe sustentar completamente la descripción.

NO incluyas:

- identificadores;
- source;
- procedencia temporal;
- puntuaciones;
- aplicabilidad.

No alteres palabras de la cita.
No reconstruyas una frase.
No combines fragmentos separados para fabricar una cita.

No aumentes ni reduzcas artificialmente la intensidad.

============================================================
DEDUPLICACIÓN Y UNIDAD SEMÁNTICA
============================================================

Dentro de una misma categoría, representa UNA sola vez una misma
manifestación o episodio emocional/fisiológico.

No dividas una evidencia completa en varios elementos cuando esos
elementos sean únicamente síntomas o partes de la misma manifestación
expresada conjuntamente.

Si una misma oración expresa conjuntamente varios signos de activación
fisiológica y todos describen el mismo episodio, crea UNA sola entrada
de ACTIVATION que preserve conjuntamente esas manifestaciones.

No generes simultáneamente:

- una entrada para toda la activación;
- otra para uno de sus síntomas;
- otra para otro síntoma;

si las entradas parciales son solamente subconjuntos de la primera.

Solo crea elementos separados cuando representen estados o
manifestaciones semánticamente distintos.

No alteres ni reconstruyas las citas para conseguir la deduplicación.

Si una cita literal más amplia contiene conjuntamente las
manifestaciones relevantes, prefiere esa cita.

La presencia legítima del mismo referente en DISTRESS y ACTIVATION
NO se considera duplicación entre categorías.

============================================================
CONTROL FINAL OBLIGATORIO
============================================================

Para cada elemento comprueba:

1. ¿Está realmente sustentado por el TEXTO A ANALIZAR?
2. ¿La descripción conserva su naturaleza emocional o fisiológica?
3. ¿La cita existe literalmente en el texto?
4. ¿La cita sustenta completamente la descripción?
5. ¿La intensidad atribuida está sustentada?
6. ¿Está en la categoría correcta?
7. ¿Está duplicado dentro de esa categoría?
8. ¿Estoy infiriendo interferencia con una acción?

Si 1, 2, 3, 4 o 5 son NO:
NO incluyas el elemento.

Si 6 es NO:
corrige la clasificación.

Si 7 es SÍ:
conserva únicamente la representación semántica mínima adecuada.

Si 8 es SÍ:
elimina la inferencia de interferencia.

Si una categoría no tiene evidencia suficiente, devuelve [].

Devuelve EXCLUSIVAMENTE el objeto JSON exigido por el schema.
No añadas explicaciones, comentarios ni texto fuera del JSON.
""".strip()
