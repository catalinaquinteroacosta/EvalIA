"""Consolidacion conservadora de PA1-PA8."""


def consolidate(original, decisions):
    results = {}

    for identity, record in original.items():
        state = record["state"]

        if identity in decisions:
            decision = decisions[identity]["decision"]

            if state == "BLOCKED" and decision != "BLOCKED":
                state = decision

            elif decision == "BLOCKED":
                state = "BLOCKED"

        results[identity] = {
            "state": state,
            "score": None,
        }

    return results


def criterion_ready(results):
    return (
        bool(results)
        and all(
            record["state"] in {
                "SUPPORTED", "NOT_SUPPORTED", "N/A"
            }
            for record in results.values()
        )
    )
