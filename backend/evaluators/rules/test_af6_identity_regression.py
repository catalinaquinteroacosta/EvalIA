
import json
from copy import deepcopy
from pathlib import Path

from backend.evaluators.rules.af6_scorer import score_af6

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "auditoria_af68"


def load(name):
    return json.loads(
        (AUDIT / name).read_text(encoding="utf-8")
    )


def build_semantic(v_result):
    integrated = load("AF6_integrado_final.json")
    semantic = deepcopy(integrated["semantic"])
    item = semantic["prior_resources"][0]

    assert item["semantic_validation"]["H"]["status"] == "supported"
    assert item["semantic_validation"]["R"]["status"] == "supported"

    item["semantic_validation"]["V"] = v_result
    return semantic


def test_af6_positive_identity_score_3():
    positive = load("AF6_identidad_positivo.json")
    assert positive["result"]["status"] == "supported"

    decision = score_af6(
        build_semantic(positive["result"])
    )

    assert decision.score == 3
    assert decision.has_h
    assert decision.has_v
    assert decision.has_r


def test_af6_different_resource_does_not_score_3():
    negative = load("AF6_identidad_adversarial.json")
    assert negative["result"]["status"] == "not_supported"

    decision = score_af6(
        build_semantic(negative["result"])
    )

    assert decision.score == 1
    assert decision.has_h
    assert not decision.has_v
    assert not decision.has_r
