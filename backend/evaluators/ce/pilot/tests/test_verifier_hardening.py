from backend.evaluators.ce.pilot.independent_verifier import build_verifier

def test_identical_sources_do_not_guess_provenance():
    v = build_verifier(indicator="CE3", user_text="Hola", response_text="Hola",
                       semantic_runner=lambda **kw: (_ for _ in ()).throw(AssertionError("No call")))
    assert v("Hola", "Hola", "Claridad") == "ambiguous"

def test_counterevidence_must_be_contiguous_in_one_source():
    v = build_verifier(indicator="CE3", user_text="abc", response_text="def",
                       semantic_runner=lambda **kw: {"verdict":"unsupported",
                           "reason":"Contradicción", "counterevidence":"abc\ndef"})
    assert v("def", "def", "Claridad") == "ambiguous"
