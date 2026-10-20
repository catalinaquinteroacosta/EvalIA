from backend.evaluators.rules.af1_scorer import score_af1


def m(*, orientation=False, status="supported"):
    return {
        "aspect": "aspecto modificable",
        "orientation": "actuar sobre M" if orientation else None,
        "semantic_validation": {
            "aspect": {"status": status},
            "orientation": (
                {"status": status}
                if orientation
                else None
            ),
        },
    }


def l(*, orientation=False, status="supported"):
    return {
        "aspect": "aspecto no modificable",
        "orientation": "orientación frente a L" if orientation else None,
        "semantic_validation": {
            "aspect": {"status": status},
            "orientation": (
                {"status": status}
                if orientation
                else None
            ),
        },
    }


def g(*, status="supported"):
    return {
        "guarantee": "resultado garantizado",
        "semantic_validation": {
            "status": status,
        },
    }


def result(modifiable=None, unmodifiable=None, guarantees=None):
    return {
        "modifiable": modifiable or [],
        "unmodifiable": unmodifiable or [],
        "control_guarantees": guarantees or [],
    }


def test_af1_zero_when_no_m_or_l():
    d = score_af1(result())
    assert d.score == 0


def test_af1_zero_when_control_guarantee_is_confirmed():
    d = score_af1(
        result(
            modifiable=[m(orientation=True)],
            unmodifiable=[l(orientation=True)],
            guarantees=[g()],
        )
    )
    assert d.score == 0
    assert d.has_control_guarantee is True


def test_af1_one_when_only_m():
    d = score_af1(
        result(modifiable=[m(orientation=True)])
    )
    assert d.score == 1


def test_af1_one_when_only_l():
    d = score_af1(
        result(unmodifiable=[l(orientation=True)])
    )
    assert d.score == 1


def test_af1_one_when_m_and_l_but_no_orientation():
    d = score_af1(
        result(
            modifiable=[m()],
            unmodifiable=[l()],
        )
    )
    assert d.score == 1


def test_af1_two_when_only_m_has_orientation():
    d = score_af1(
        result(
            modifiable=[m(orientation=True)],
            unmodifiable=[l()],
        )
    )
    assert d.score == 2
    assert d.has_v_m is True
    assert d.has_v_l is False


def test_af1_two_when_only_l_has_orientation():
    d = score_af1(
        result(
            modifiable=[m()],
            unmodifiable=[l(orientation=True)],
        )
    )
    assert d.score == 2
    assert d.has_v_m is False
    assert d.has_v_l is True


def test_af1_three_when_both_classes_have_orientation():
    d = score_af1(
        result(
            modifiable=[m(orientation=True)],
            unmodifiable=[l(orientation=True)],
        )
    )
    assert d.score == 3


def test_af1_ambiguous_components_do_not_count():
    d = score_af1(
        result(
            modifiable=[m(
                orientation=True,
                status="ambiguous",
            )],
            unmodifiable=[l(
                orientation=True,
                status="ambiguous",
            )],
            guarantees=[g(status="ambiguous")],
        )
    )

    assert d.score == 0
    assert d.has_m is False
    assert d.has_l is False
    assert d.has_control_guarantee is False


def test_af1_ambiguous_guarantee_does_not_force_zero():
    d = score_af1(
        result(
            modifiable=[m(orientation=True)],
            unmodifiable=[l(orientation=True)],
            guarantees=[g(status="ambiguous")],
        )
    )

    assert d.score == 3
    assert d.has_control_guarantee is False