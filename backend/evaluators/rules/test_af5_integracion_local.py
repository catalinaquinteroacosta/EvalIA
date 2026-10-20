"""Pruebas de frontera AF5 con proveedor semántico simulado; no usan tokens."""
from backend.evaluators.semantic import af_ai_af5 as af5
from backend.evaluators.semantic.af_evidence_recovery import AFEvidenceRecoveryError


def test_recovery_invalid_quote_does_not_abort(monkeypatch):
    def broken(**kwargs):
        raise AFEvidenceRecoveryError('cita no literal')
    monkeypatch.setattr(af5, 'recover_literal_evidence', broken)
    result = af5._validate_c(
        item={'remaining_choice':'ordenar habitación',
              'choice_evidence':{'quote':'habitaci?n'},
              'choice_relation':{'status':'supported'}},
        current_ai='Puedes ordenar tu habitación.', model='fake', timeout=1,
    )
    assert result['status'] == 'not_supported'


def test_implicit_acceptance_uses_literal_l_and_c(monkeypatch):
    captured = {}
    def fake_validator(**kwargs):
        captured.update(kwargs)
        return {'status':'supported','reason':'simulado'}
    monkeypatch.setattr(af5, 'validate_semantic_entailment', fake_validator)
    item={'limit_evidence':{'quote':'El examen ya fue presentado'},
          'choice_evidence':{'quote':'preparar la siguiente clase'}}
    response='El examen ya fue presentado. Puedes preparar la siguiente clase.'
    result=af5._validate_implicit_acceptance_with_choice(item=item,current_ai=response,model='fake',timeout=1)
    assert result['status']=='supported'
    assert captured['evidence']=='El examen ya fue presentado\npreparar la siguiente clase'
    assert captured['local_context']==response


def test_implicit_acceptance_rejects_nonliteral_evidence(monkeypatch):
    def must_not_call(**kwargs):
        raise AssertionError('No consultar el modelo sin citas literales')
    monkeypatch.setattr(af5, 'validate_semantic_entailment', must_not_call)
    item={'limit_evidence':{'quote':'La entrevista ya ocurrió'},
          'choice_evidence':{'quote':'habitaci?n'}}
    result=af5._validate_implicit_acceptance_with_choice(
        item=item,current_ai='La entrevista ya ocurrió. Puedes ordenar tu habitación.',model='fake',timeout=1)
    assert result['status']=='not_supported'


def test_joint_explicit_uses_three_verified_literal_quotes(monkeypatch):
    captured = {}
    def fake_validator(**kwargs):
        captured.update(kwargs)
        return {"status": "supported"}
    monkeypatch.setattr(af5, "validate_semantic_entailment", fake_validator)
    ai = ("El examen ya se presentó. Puedes esperar sin exigir tranquilidad. "
          "Prepara la siguiente clase.")
    item = {"semantic_validation": {
        "L": {"status": "supported", "verified_quote": "El examen ya se presentó"},
        "A": {"status": "supported", "verified_quote": "Puedes esperar sin exigir tranquilidad"},
        "C": {"status": "supported", "verified_quote": "Prepara la siguiente clase"},
    }}
    result = af5._validate_explicit_lac_coherence(
        item=item, current_ai=ai, model="fake", timeout=1)
    assert result["status"] == "supported"
    assert captured["evidence"] == ("El examen ya se presentó\n"
                                    "Puedes esperar sin exigir tranquilidad\n"
                                    "Prepara la siguiente clase")


def test_joint_explicit_rejects_unverified_quotes_without_tokens(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("No consultar modelo con evidencia inválida")
    monkeypatch.setattr(af5, "validate_semantic_entailment", forbidden)
    item = {"semantic_validation": {
        "L": {"status": "supported", "verified_quote": "La entrevista ya pasó"},
        "A": {"status": "supported", "verified_quote": "Acepta la espera"},
        "C": {"status": "supported", "verified_quote": "cita inventada"},
    }}
    result = af5._validate_explicit_lac_coherence(
        item=item, current_ai="La entrevista ya pasó. Acepta la espera. Ordena la habitación.",
        model="fake", timeout=1)
    assert result["status"] == "not_supported"
