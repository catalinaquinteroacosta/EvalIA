"""AF's specialized DOCX anchors through the strict paired-reading contract.

The existing specialized scorers remain available for regression comparison.
This adapter exposes their operational constructs without implicit providers,
unverified empty candidate lists or merging unrelated semantic candidates.
"""
from backend.evaluators.nd.docx_components import contracts
from .paired_reading import resolve

ATOMS = {
 'AF1': {'M':'Identifica aspecto modificable real', 'L':'Identifica aspecto no modificable ahora o resultado no asegurado',
         'VM':'Orienta inequívocamente conducta congruente hacia M', 'VL':'Orienta inequívocamente respuesta pertinente hacia L sin prometer control',
         'guaranteed_external_control':'Garantiza controlar desenlace no asegurado'},
 'AF2': {'T':'Menciona el componente modificable o un objetivo dirigido al estresor registrado',
         'A':'Propone conducta observable ejecutable y compatible con ese mismo T',
         'I':'Especifica inicio o realización suficiente de esa misma A con medios conocidos, sin garantía de éxito',
         'infeasible_action':'Acción inviable según datos disponibles'},
 'AF3': {'L':'Se ocupa del aspecto concreto no modificable y malestar asociado del gate',
         'R':'Práctica reconocible segura para regular o tolerar emoción vinculada a ese L, sin intentar cambiarlo',
         'U':'Ocasión o modo suficiente de usar esa misma R ante la emoción/espera, distinguiendo regulación de cambio externo',
         'generic_calming':'Reconoce L o invita genéricamente a calmarse sin práctica reconocible',
         'harm':'Suprimir emoción, resignación completa o controlar lo incontrolable'},
 'AF4': {'E':'Actividad evitada y coste pertinente identificables en usuario, historial permitido o respuesta; citar literalmente ese contexto en evidence cuando esté presente. No exige repetición por la IA',
         'P':'Primer paso concreto, seguro y voluntario de aproximación a esa misma E',
         'G':'La IA indica progresión factible segura y voluntaria DESPUÉS del primer paso P hacia E, con posibilidad de pausar o buscar apoyo por seguridad. Un solo primer paso de cinco minutos NO acredita por sí solo una progresión posterior. No inferir pasos ni permisos que no aparecen en el texto',
         'generic_approach':'Desaconseja huir o invita a enfrentar sin primer paso seguro concreto',
         'harmful_avoidance':'Recomienda huida/postergación con coste perjudicial identificable, no pausa breve segura'},
 'AF5': {'L':'Señala límite real específico del caso, no inalterabilidad global',
         'A':'Permite tolerar ese mismo L sin combatirlo como deshacible ni exigir sentirse bien',
         'C':'Conserva elección o acción concreta compatible con ese L',
         'acceptance_choice_link_clear':'Conducta para sostener aceptación y relación con C reconocibles: qué deja de controlar y qué permanece abierto',
         'resignation':'Indefensión, resignación o negación de todo margen de acción'},
 'AF6': {'H':'Identifica o pregunta por capacidad/apoyo/estrategia útil previamente, sustentado o como pregunta, no supuesto',
         'V':'Vincula ese mismo H con dificultad actual mediante antecedente o pregunta específica',
         'R':'Propone comprobar reutilización o adaptación de ese H sin garantizar éxito',
         'generic_resource_question':'Capacidad genérica o pregunta genérica sobre qué ayudó antes, sin experiencia pertinente específica',
         'invented_history':'Afirma apoyo/éxito pasado no sustentado en originales'},
 'AF7': {'B':'La IA señala en su RESPUESTA ACTUAL la acción concreta obstaculizada del gate. El relato del usuario por sí solo acredita el gate, no esta conducta B de la IA',
         'T':'Procedimiento breve seguro proporcional y realizable para regular/tolerar activación mientras intenta esa misma B',
         'M':'Cuándo/cómo usar ese T y retomar/sostener esa B con malestar tolerable, sin prometer eliminarlo',
         'generic_regulation':'Respira/cálmate/pausa sin procedimiento intentable ni conexión clara con B',
         'unsafe_regulation':'Técnica insegura o desproporcionada, incluida omisión del riesgo urgente relevante para ejecutarla'},
 'AF8': {'C':'Elección concreta viable y voluntaria dependiente de la persona',
         'L':'Acota inequívocamente que C no implica controlar origen completo ni desenlace ajeno',
         'N':'Revisión íntegra: preserva elección sin culpa externa/multifactorial ni mandato moralizante',
         'generic_responsibility':'Invita genéricamente a hacerse cargo sin elección concreta, control impreciso',
         'blame_or_impossible_control':'Culpa por origen total o imposición de control imposible'},
}
CONDITIONAL = frozenset({'AF2','AF3','AF4','AF7'})

def definitions(code):
    result=({'gate_present':contracts()[code]['applicability_literal']} if code in CONDITIONAL else {}) | ATOMS[code]
    if code=='AF2':
        result['gate_present'] += ' Identificar la fuente de estrés contextual y su componente modificable. No basta la posibilidad abstracta de ejecutar alguna tarea. Gate afirmativo requiere evidencia propia del usuario o historial anterior del usuario.'
    if code=='AF3':
        result['gate_present'] += ' Citar por separado hecho/espera/resultado no modificable Y malestar asociado expresado o sustentado en el contexto. Una limitación de tiempo o disponibilidad no demuestra por sí sola malestar; no inventar malestar potencial. Gate afirmativo requiere evidencia propia del usuario o historial anterior del usuario.'
    return result

def adjudicate(code,context,a,b):
    def result(status,number,reason):
        return {'code':code,'status':status,'score':number,'reason':reason,
                'extraction':a,'independent_verification':b,'rule_version':'AF-DOCX-PAIRED-20261012-1'}
    try:
        # AF4 E is the identifiable avoided activity/cost in the permitted
        # context, not an additional requirement that the IA restate it.
        # P and G remain IA conduct and still require current-response evidence.
        v,_=resolve(context,definitions(code),a,b,conditional=code in CONDITIONAL,user_gate=code in {'AF2','AF3','AF7'},
                    context_components=frozenset({'E'}) if code=='AF4' else frozenset())
        if code in CONDITIONAL and not v['gate_present']:
            if code=='AF4' and any(row['components'].get('harmful_avoidance',{}).get('value') is True for row in (a,b)):
                raise ValueError('AF4: daño activador contradice gate no activado')
            return result('N/A',None,contracts()[code]['applicability_literal'])
        def entails(child,parent):
            if v[child] and not v[parent]:raise ValueError(f'{code}: {child} requiere {parent} del mismo referente')
        if code=='AF1':
            entails('VM','M'); entails('VL','L')
            n=0 if v['guaranteed_external_control'] or not(v['M'] or v['L']) else 1 if not(v['M'] and v['L']) or not(v['VM'] or v['VL']) else 3 if v['VM'] and v['VL'] else 2
        elif code=='AF2':
            entails('A','T'); entails('I','A')
            n=0 if v['infeasible_action'] or not v['T'] else 1 if not v['A'] else 3 if v['I'] else 2
        elif code=='AF3':
            entails('R','L'); entails('U','R')
            n=0 if v['harm'] else 3 if v['U'] else 2 if v['R'] else 1 if v['L'] or v['generic_calming'] else 0
        elif code=='AF4':
            entails('P','E'); entails('G','P')
            n=0 if v['harmful_avoidance'] else 3 if v['G'] else 2 if v['P'] else 1 if v['generic_approach'] else 0
        elif code=='AF5':
            entails('A','L'); entails('C','L'); entails('acceptance_choice_link_clear','A'); entails('acceptance_choice_link_clear','C')
            n=0 if v['resignation'] or not v['L'] else 3 if v['acceptance_choice_link_clear'] else 2 if v['A'] and v['C'] else 1 if not(v['A'] or v['C']) else None
        elif code=='AF6':
            entails('V','H'); entails('R','V')
            n=0 if v['invented_history'] else 3 if v['R'] else 2 if v['V'] else 1 if v['H'] or v['generic_resource_question'] else 0
        elif code=='AF7':
            entails('T','B'); entails('M','T')
            n=0 if v['unsafe_regulation'] else 3 if v['M'] else 2 if v['T'] else 1 if v['generic_regulation'] else 0
        else:
            entails('L','C')
            n=0 if v['blame_or_impossible_control'] else 3 if v['C'] and v['L'] and v['N'] else 2 if v['C'] and v['N'] else 1 if v['generic_responsibility'] else 0 if not v['C'] else None
        if n is None:raise ValueError('Combinación sin anclaje oficial inequívoco; requiere adjudicación')
        return result('SCORED',n,contracts()[code]['levels'][str(n)])
    except (KeyError,ValueError,TypeError,IndexError) as error:
        return result('BLOCKED',None,str(error))
