from backend.evaluators.ce.ce_a import claim_verifier, claim_fidelity_auditor

def test_claim_prompt_requires_original_language_and_subject(monkeypatch):
    prompts = []
    monkeypatch.setattr(claim_verifier, "get_semantic_identity", lambda **kw: {"model":"test"})
    def fake_semantic(**kw):
        prompts.append(kw["prompt"])
        return {"claims":["La respuesta ofrece una muestra de cuidado."], "decomposition_complete":True, "reason":"Fiel"}
    monkeypatch.setattr(claim_verifier, "run_structured_semantic", fake_semantic)
    monkeypatch.setattr(claim_verifier, "audit_claim_fidelity", lambda *a,**kw: {"verdict":"ambiguous","reason":"Prueba local","findings":[]})
    result=claim_verifier.verify_claims("La respuesta ofrece una muestra de cuidado.", "Cuídate mucho.", "Cuídate mucho.", use_cache=False)
    assert result["verdict"] == "ambiguous"
    assert "SAME LANGUAGE" in prompts[0]
    assert "original subject" in prompts[0]

def test_fidelity_prompt_flags_mistranslation(monkeypatch):
    prompts=[]
    monkeypatch.setattr(claim_fidelity_auditor, "get_semantic_identity", lambda **kw: {"model":"test"})
    def fake_semantic(**kw):
        prompts.append(kw["prompt"])
        return {"verdict":"unfaithful", "reason":"Sujeto inventado", "findings":["Sujeto inventado"]}
    monkeypatch.setattr(claim_fidelity_auditor, "run_structured_semantic", fake_semantic)
    claim_fidelity_auditor.audit_claim_fidelity("La respuesta ofrece una muestra de cuidado.", ["The dice says care"],use_cache=False)
    assert "invented subjects" in prompts[0]
