
from pathlib import Path
import json

import pytest


ROOT = Path(__file__).resolve().parents[4]

PILOTS = ROOT / "resultados/piloto_integral_ce2_ce10"


def load_case(filename):
    path = PILOTS / filename

    if not path.exists():
        pytest.skip(
            f"No existe el piloto hist?rico: {filename}"
        )

    data = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    return data["cases"][0]


def literal_quote_exists(claim, case):
    source = claim.get("source")
    quote = claim.get("quote")

    if not isinstance(quote, str) or not quote:
        return False

    if source == "user":
        text = case.get("user_message", "")
    elif source == "response":
        text = case.get("assistant_response", "")
    else:
        return False

    return quote in text




def test_ce7_historical_nonliteral_quote_rejected():
    case = load_case(
        "integral_CE7_1_20261005T203602Z.json"
    )

    claims = case["semantic_calls"][0]["result"]["claims"]

    assert len(claims) == 3

    assert literal_quote_exists(claims[0], case)
    assert literal_quote_exists(claims[1], case)

    assert not literal_quote_exists(claims[2], case)

    # The extractor changed the verb form.
    assert claims[2]["quote"].startswith("elige ")

    # The original response contains "elegir", not "elige".
    assert "intenta elegir " in case["assistant_response"]

def test_ce8_historical_user_quote_is_not_literal():
    case = load_case(
        "integral_CE8_1_20261005T211546Z.json"
    )

    extraction = case["semantic_calls"][0]["result"]

    user_claims = [
        claim for claim in extraction["claims"]
        if claim.get("source") == "user"
    ]

    assert user_claims

    assert any(
        not literal_quote_exists(claim, case)
        for claim in user_claims
    )


def test_ce8_response_quote_is_literal():
    case = load_case(
        "integral_CE8_1_20261005T211546Z.json"
    )

    extraction = case["semantic_calls"][0]["result"]

    response_claims = [
        claim for claim in extraction["claims"]
        if claim.get("source") == "response"
    ]

    assert response_claims

    assert all(
        literal_quote_exists(claim, case)
        for claim in response_claims
    )
