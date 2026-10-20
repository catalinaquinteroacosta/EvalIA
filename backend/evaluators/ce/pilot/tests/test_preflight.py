from backend.evaluators.ce.pilot.preflight import inspect_modules, INDICATORS

def test_covers_five():
    assert set(INDICATORS) == {'CE1', 'CE2', 'CE3', 'CE4', 'CE5'}

def test_does_not_claim_readiness():
    def importer(_):
        class Dummy:
            pass
        for _, (name, fn) in INDICATORS.items():
            if _ == name:
                setattr(Dummy, fn, lambda: None)
        return Dummy
    r = inspect_modules(importer)
    assert all(not x['production_ready'] for x in r.values())

def test_missing_import_is_detected():
    def missing(_):
        raise ImportError('missing')
    assert all(x['imports'] == 'failed' for x in inspect_modules(missing).values())
