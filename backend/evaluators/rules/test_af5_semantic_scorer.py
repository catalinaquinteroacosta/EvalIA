from backend.evaluators.rules.af5_scorer import score_af5


def _item(l="not_supported", a="not_supported", c="not_supported", implicit=None, coherence="supported"):
    result = {
        "semantic_validation": {
            "L": {"status": l},
            "A": {"status": a},
            "C": {"status": c},
        }
    }
    result["explicit_lac_coherence"] = {"status": coherence}
    if implicit is not None:
        result["implicit_acceptance"] = {"status": implicit}
    return result


def _semantic(*items, resignation_statuses=()):
    return {
        "acceptance": list(items),
        "resignation_or_helplessness": [
            {
                "semantic_validation": {
                    "status": status,
                }
            }
            for status in resignation_statuses
        ],
    }


def test_af5_zero_without_l():
    d = score_af5(
        semantic_result=_semantic()
    )

    assert d.score == 0
    assert d.applicable is True
    assert d.has_l is False
    assert d.resignation_or_helplessness is False


def test_af5_one_l_only():
    d = score_af5(
        semantic_result=_semantic(
            _item(l="supported")
        )
    )

    assert d.score == 1
    assert d.has_l is True
    assert d.has_a is False
    assert d.has_c is False


def test_af5_one_l_plus_a_without_c():
    d = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="supported",
            )
        )
    )

    assert d.score == 1
    assert d.has_l is True
    assert d.has_a is True
    assert d.has_c is False


def test_af5_two_l_plus_c_without_a():
    d = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                c="supported",
                implicit="supported",
            )
        )
    )

    assert d.score == 2
    assert d.has_l is True
    assert d.has_a is False
    assert d.has_c is True


def test_af5_three_requires_l_a_c_in_same_entry():
    d = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="supported",
                c="supported",
            )
        )
    )

    assert d.score == 3
    assert d.has_l is True
    assert d.has_a is True
    assert d.has_c is True


def test_af5_does_not_mix_components_across_entries():
    d = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="supported",
            ),
            _item(
                l="supported",
                c="supported",
                implicit="supported",
            ),
        )
    )

    assert d.score != 3
    assert d.score == 2


def test_af5_ambiguous_never_counts_as_positive():
    d = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="ambiguous",
                c="ambiguous",
            )
        )
    )

    assert d.score == 1
    assert d.has_l is True
    assert d.has_a is False
    assert d.has_c is False


def test_af5_resignation_caps_at_zero():
    d = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="supported",
                c="supported",
            ),
            resignation_statuses=("supported",),
        )
    )

    assert d.score == 0
    assert d.resignation_or_helplessness is True


def test_af5_ambiguous_resignation_does_not_cap():
    d = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="supported",
                c="supported",
            ),
            resignation_statuses=("ambiguous",),
        )
    )

    assert d.score == 3
    assert d.resignation_or_helplessness is False


def test_af5_resignation_dominates_even_if_a_was_supported():
    d = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="supported",
            ),
            resignation_statuses=("supported",),
        )
    )

    assert d.score == 0
    assert d.resignation_or_helplessness is True


def test_af5_adversarial_unrelated_activity_not_level_two():
    """Reconocer L y sugerir una actividad no demuestra A."""
    result = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="not_supported",
                c="supported",
                implicit="not_supported",
            )
        )
    )
    assert result.score < 2


def test_af5_adversarial_no_cross_entry_full_acceptance():
    """No se deben combinar componentes de entradas distintas."""
    result = score_af5(
        semantic_result=_semantic(
            _item(l="supported", a="supported"),
            _item(l="supported", c="supported"),
        )
    )
    assert result.score < 3


def test_af5_explicit_components_without_joint_coherence_do_not_score_three():
    decision = score_af5(semantic_result=_semantic(
        _item(l="supported", a="supported", c="supported",
              coherence="not_supported")))
    assert decision.score == 1


def test_af5_explicit_components_with_ambiguous_joint_coherence_do_not_score_three():
    decision = score_af5(semantic_result=_semantic(
        _item(l="supported", a="supported", c="supported",
              coherence="ambiguous")))
    assert decision.score == 1


def test_af5_joint_coherence_fallback_to_implicit_level_two():
    """Una coherencia conjunta fallida no elimina un L+C v?lido."""
    decision = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="supported",
                c="supported",
                coherence="ambiguous",
                implicit="supported",
            )
        )
    )
    assert decision.score == 2
    assert decision.has_l is True
    assert decision.has_a is False
    assert decision.has_c is True


def test_af5_joint_coherence_without_implicit_stays_at_one():
    """No se concede nivel 2 sin relaci?n impl?cita confirmada."""
    decision = score_af5(
        semantic_result=_semantic(
            _item(
                l="supported",
                a="supported",
                c="supported",
                coherence="not_supported",
                implicit="not_supported",
            )
        )
    )
    assert decision.score == 1
    assert decision.has_l is True
    assert decision.has_a is False
    assert decision.has_c is False
