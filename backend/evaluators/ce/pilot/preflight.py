"""EvalIA CE1-CE5: auditoría local de preparación. Nunca llama a OpenAI."""
from importlib import import_module

INDICATORS = {
    'CE1': ('backend.evaluators.ce.ce_a.ce1_integrated', 'evaluate_ce1_integrated'),
    'CE2': ('backend.evaluators.ce.ce_b.ce2_provider_bridge', 'extract_ce2_draft'),
    'CE3': ('backend.evaluators.ce.ce_c.ce3_provider_bridge', 'extract_ce3_draft'),
    'CE4': ('backend.evaluators.ce.ce_d.ce4_provider_bridge', 'extract_ce4_draft'),
    'CE5': ('backend.evaluators.ce.ce_e.ce5_provider_bridge', 'extract_ce5_draft'),
}

def inspect_modules(importer=import_module):
    result = {}
    for code, (module_name, function_name) in INDICATORS.items():
        try:
            module = importer(module_name)
            if not callable(getattr(module, function_name, None)):
                raise AttributeError(f'{function_name} no disponible')
            result[code] = {'imports': 'ok', 'production_ready': False,
                            'reason': 'Falta demostrar extracción + verificación independiente + puntuación integrada'}
        except (ImportError, AttributeError) as exc:
            result[code] = {'imports': 'failed', 'production_ready': False, 'reason': str(exc)}
    return result

if __name__ == '__main__':
    import json
    print(json.dumps(inspect_modules(), indent=2, ensure_ascii=False))
