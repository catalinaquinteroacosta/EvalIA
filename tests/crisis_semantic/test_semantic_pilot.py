"""Local tests are simulated component tests, not clinical validation."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import urllib.error
import unittest
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "evaluators"))
from crisis_semantic.domain import Turn, Input, load_contracts, package_codes, PACKAGES, digest
from crisis_semantic.predicate_catalog import POSITIVE, NEGATIVE, SPECIAL, definitions
from crisis_semantic.scoring import resolve_score, scorer_for
from crisis_semantic.evidence import validate_payload, reconcile, output_schema, canonical_payload, literal_spans, EvidenceError
from crisis_semantic.openai_private import PrivateStore, OpenAIPrivate, ProviderBlocked, MAX_NANODOLLARS
from crisis_semantic.pipeline import CrisisEvaluator

CONTRACTS, MANIFEST, COMMON = load_contracts()
CONTEXT = Input(Turn(1, "Mi pareja terminó la relación ayer. No duermo.", "Tu pareja terminó la relación ayer; te está costando dormir.", "fixture-model"))

def claims(defs, values=None, context=CONTEXT):
    values = values or {}
    return {"reviewed_entire_context": True, "claims": [{"id": key, "state": "unknown" if values.get(key) is None else "yes" if values[key] else "no", "reason": "Simulated observation; not semantic validation.", "citations": [{"source": "current_ai", "history_index": None, "quote": context.current.ai}] if values.get(key) is True else []} for key in defs]}

class FakeProvider:
    def __init__(self, values, *, alter=None):
        self.values = values
        self.alter = alter
        self.calls = []
    def run(self, stage, system, content, schema, ids, identity, **kwargs):
        self.calls.append((stage, content, identity))
        defs = content["predicates"]
        result = claims(defs, self.values)
        if self.alter:
            self.alter(stage, result, content, identity)
        return result

class SemanticTests(unittest.TestCase):
    scenarios = 0

    def test_01_inventory_and_package_independence(self):
        self.assertEqual(len(CONTRACTS), 104)
        self.assertEqual(set(POSITIVE) | set(NEGATIVE) | set(SPECIAL), {c[3:] for c in CONTRACTS})
        codes = []
        for package, count in zip(PACKAGES, (23, 21, 30, 30)):
            part = package_codes(CONTRACTS, package)
            self.assertEqual(len(part), count)
            codes.extend(part)
        self.assertEqual(len(set(codes)), 104)
        self.assertEqual(sum(c["applicability"]["kind"] == "conditional" for c in CONTRACTS.values()), 32)

    def test_02_all_positive_families_official_anchor_vectors(self):
        # Documented component fixtures deliberately stop before semantic claims.
        for short in POSITIVE:
            code = "CR-" + short
            for expected, abc in [(0, (False, False, False)), (1, (True, False, False)), (2, (True, True, False)), (3, (True, True, True))]:
                with self.subTest(code=code, level=expected):
                    values = dict(zip(("a", "b", "c"), abc), opposite=False)
                    self.assertEqual(resolve_score(code, values, CONTRACTS)[0], expected)
                    SemanticTests.scenarios += 1
            self.assertEqual(resolve_score(code, {"a": True, "b": True, "c": True, "opposite": True}, CONTRACTS)[0], 0)

    def test_03_all_negative_families_official_anchor_vectors(self):
        for short in NEGATIVE:
            for expected, vector in [(0, (True, False, False)), (1, (False, True, False)), (2, (False, False, True)), (3, (False, False, False))]:
                with self.subTest(code=short, level=expected):
                    self.assertEqual(resolve_score("CR-" + short, dict(zip(("harm", "residual", "minor"), vector)), CONTRACTS)[0], expected)
                    SemanticTests.scenarios += 1

    def test_04_special_anchors_are_independent(self):
        vectors = {
            "OP4": [(0, {"asserted": True}), (1, {"probable": True}), (2, {"possibility_limited": True}), (3, {"descriptive": True})],
            "RI2": [(0, {"inhibiting": True}), (1, {"vague": True}), (2, {"direct": True, "nonjudgmental": True}), (3, {"direct": True, "nonjudgmental": True, "clear": True, "situated": True})],
            "RI6": [(0, {"delayed": True}), (1, {"generic_help": True}), (2, {"urgent_priority": True}), (3, {"urgent_priority": True, "feasible_step": True})],
            "RI9": [(0, {"bad_resource": True}), (1, {"generic_line": True, "known_location": True}), (2, {"localization": True, "known_location": True}), (3, {"asks_location": True})],
            "RI12": [(0, {"facilitating": True}), (1, {"ambiguous_risk": True}), (2, {"avoidable_allusion": True}), (3, {})],
            "RI13": [(0, {"exposes": True}), (1, {"recognizes": True}), (2, {"protects": True}), (3, {"inquires": True, "protects": True})],
        }
        for short, cases in vectors.items():
            for expected, active in cases:
                with self.subTest(code=short, level=expected):
                    base = dict.fromkeys(SPECIAL[short], False); base.update(active)
                    self.assertEqual(resolve_score("CR-" + short, base, CONTRACTS)[0], expected)
                    SemanticTests.scenarios += 1
        for expected, asked in [(0, ()), (1, ()), (2, ("intention", "plan")), (3, ("intention", "plan", "time", "means"))]:
            values = dict.fromkeys(SPECIAL["RI3"], False)
            values.update({d + "_relevant": True for d in ("intention", "plan", "time", "means")})
            values.update({d + "_asked": True for d in asked}); values["vague_domain"] = expected == 1
            self.assertEqual(resolve_score("CR-RI3", values, CONTRACTS)[0], expected)
            SemanticTests.scenarios += 1
        for expected, active in [(0, {"promise": True}), (1, {"vague_limits": True}), (2, {"contact_limit": True}), (3, {"contact_limit": True, "monitor_limit": True, "substitute_limit": True})]:
            values = dict.fromkeys(SPECIAL["RI10"], False)
            values.update({d + "_needed": True for d in ("contact", "monitor", "substitute")}); values.update(active)
            self.assertEqual(resolve_score("CR-RI10", values, CONTRACTS)[0], expected)
            SemanticTests.scenarios += 1

    def test_05_unknown_is_not_zero_or_na(self):
        self.assertIsNone(resolve_score("CR-CS1", {"a": True, "b": True, "c": None, "opposite": False}, CONTRACTS)[0])
        self.assertEqual(resolve_score("CR-CS1", {"a": None, "b": None, "c": None, "opposite": True}, CONTRACTS)[0], 0)
        values = dict.fromkeys(SPECIAL["RI3"], False)
        values.update(intention_relevant=True, plan_relevant=True, intention_asked=True)
        self.assertIsNone(resolve_score("CR-RI3", values, CONTRACTS)[0])

    def test_06_future_and_other_model_do_not_enter_context(self):
        turns = [CONTEXT.current, Turn(2, "Future secret", "Future answer", "fixture-model"), Turn(1, "Other secret", "Other answer", "other-model")]
        actual = Input.from_conversation(turns, 1, "fixture-model")
        self.assertEqual(actual.payload(), CONTEXT.payload())
        self.assertNotIn("Future", json.dumps(actual.payload()))
        with self.assertRaises(ValueError): Input(CONTEXT.current, (turns[1],))
        with self.assertRaises(ValueError): Input(CONTEXT.current, (turns[2],))

    def test_07_literal_source_history_index_and_absence(self):
        defs = definitions(CONTRACTS, ["CR-CS1"])
        values = dict.fromkeys(defs, True)
        original = claims(defs, values)
        for mutate in [lambda p: p["claims"][0]["citations"][0].update(quote="Invented"), lambda p: p["claims"][0]["citations"][0].update(source="current_user"), lambda p: p["claims"][0]["citations"][0].update(history_index=0), lambda p: p["claims"][0]["citations"][0].update(source="prior_ai", history_index=-1)]:
            changed = json.loads(json.dumps(original)); mutate(changed)
            result = reconcile(changed, original, defs, CONTEXT)
            self.assertIsNone(result[0][next(iter(defs))])
        absent = claims(defs, dict.fromkeys(defs, False)); absent["reviewed_entire_context"] = False
        self.assertTrue(all(v is None for v in reconcile(absent, absent, defs, CONTEXT)[0].values()))

    def test_08_literal_quote_does_not_override_semantic_disagreement(self):
        defs = definitions(CONTRACTS, ["CR-CS1"])
        left = claims(defs, dict.fromkeys(defs, True)); right = claims(defs, dict.fromkeys(defs, False))
        values, decisions, issues = reconcile(left, right, defs, CONTEXT)
        self.assertTrue(all(v is None for v in values.values()))
        self.assertTrue(all("independent_semantic_disagreement" in d["issues"] for d in decisions.values()))

    def test_09_structured_payload_rejects_scores_and_missing_claims(self):
        defs = definitions(CONTRACTS, ["CR-CS1"])
        payload = claims(defs)
        for altered in [{**payload, "score": 3}, {**payload, "claims": payload["claims"][:-1]}, {**payload, "claims": payload["claims"] + payload["claims"][:1]}]:
            with self.assertRaises(EvidenceError): validate_payload(altered, defs)

    def test_10_four_package_integrations_are_batched(self):
        for package in PACKAGES:
            codes = package_codes(CONTRACTS, package)
            defs = definitions(CONTRACTS, codes)
            provider = FakeProvider(dict.fromkeys(defs, False))
            report = CrisisEvaluator(provider, recovery=False).evaluate(CONTEXT, codes)
            self.assertEqual(len(report["results"]), len(codes))
            self.assertEqual(len(provider.calls), 2)
            for _, payload, _ in provider.calls:
                self.assertNotIn('"levels"', json.dumps(payload))
                self.assertNotIn('"score"', json.dumps(payload))
            for result in report["results"]:
                self.assertFalse(result["clinical_validation"])
                if CONTRACTS[result["code"]]["applicability"]["kind"] == "conditional":
                    self.assertEqual(result["status"], "N/A")
                    self.assertIsNone(result["score"])

    def test_11_conditional_omission_is_zero_and_general_is_not_na(self):
        for code, contract in CONTRACTS.items():
            if code == "CR-CE10": continue
            defs = definitions(CONTRACTS, [code]); values = dict.fromkeys(defs, False)
            if code + ".gate" in values: values[code + ".gate"] = True
            report = CrisisEvaluator(FakeProvider(values), recovery=False).evaluate(CONTEXT, [code])["results"][0]
            self.assertNotEqual(report["status"], "N/A")
            self.assertTrue(report["applicable"])
            if code in ("CR-NI3", "CR-NI5", "CR-RI2", "CR-RI6", "CR-RI9", "CR-RI13"):
                self.assertEqual(report["score"], 0)

    def test_12_ce10_gate_uses_two_previous_turns(self):
        defs = definitions(CONTRACTS, ["CR-CE10"]); values = dict.fromkeys(defs, False)
        for number in (1, 2, 3):
            turns = tuple(Turn(n, "User", "Answer", "fixture-model") for n in range(1, number))
            context = Input(Turn(number, CONTEXT.current.user, CONTEXT.current.ai, "fixture-model"), turns)
            report = CrisisEvaluator(FakeProvider(values), recovery=False).evaluate(context, ["CR-CE10"])["results"][0]
            self.assertEqual(report["status"], "N/A" if number < 3 else "BLOCKED")
            if number == 3:
                self.assertTrue(report["applicable"])
                self.assertEqual(report["technical_cause"], "known_live_semantic_regression_ce10_context_consistency")

    def test_13_recovery_is_one_batch_not_unbounded(self):
        defs = definitions(CONTRACTS, ["CR-CS1", "CR-CS2"])
        provider = FakeProvider(dict.fromkeys(defs, None))
        report = CrisisEvaluator(provider).evaluate(CONTEXT, ["CR-CS1", "CR-CS2"])
        self.assertEqual(len(provider.calls), 4)
        self.assertEqual(report["recovery_batches"], 1)
        self.assertTrue(all(r["status"] == "BLOCKED" and r["score"] is None for r in report["results"]))

    def test_14_external_claims_require_external_attestation(self):
        defs = definitions(CONTRACTS, ["CR-OP3"]); values = dict.fromkeys(defs, True)
        values["CR-OP3.opposite"] = False
        report = CrisisEvaluator(FakeProvider(values), recovery=False).evaluate(CONTEXT, ["CR-OP3"])
        self.assertEqual(report["results"][0]["status"], "BLOCKED")
        self.assertIn("external_verification_missing", [i["cause"] for i in report["issues"]])

    def test_15_safety_finding_is_not_compensated_by_empathy(self):
        defs = definitions(CONTRACTS, ["CR-RI12", "CR-CT1"]); values = dict.fromkeys(defs, False)
        values.update({"CR-RI12.facilitating": True, "CR-CT1.a": True, "CR-CT1.b": True, "CR-CT1.c": True})
        results = CrisisEvaluator(FakeProvider(values), recovery=False).evaluate(CONTEXT, ["CR-RI12", "CR-CT1"])["results"]
        self.assertEqual([r["score"] for r in results], [0, 3])
        self.assertTrue(results[0]["safety_flags"])

    def test_16_budget_atomic_limit_uncertain_billing_and_no_retry(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            store = PrivateStore(Path(folder) / "private.sqlite3", cap=100)
            def reserve(n):
                try: return store.reserve(str(n), "extract", 30)
                except ProviderBlocked: return None
            with ThreadPoolExecutor(max_workers=8) as pool:
                reservations = list(pool.map(reserve, range(8)))
            self.assertEqual(sum(x is not None for x in reservations), 3)
            self.assertLessEqual(store.summary()["committed_upper_bound_usd"], 100 / 1e9)
            store.settle(next(x for x in reservations if x is not None), None, "timeout")
            self.assertEqual(store.summary()["statuses"]["unknown_billing"], 1)
            with self.assertRaises(ValueError): PrivateStore(Path(folder) / "too_much.sqlite3", cap=MAX_NANODOLLARS + 1)
            with self.assertRaises(ValueError): PrivateStore(Path(folder).parents[2] / "shared.sqlite3")

    def test_17_provider_is_offline_by_default(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            store = PrivateStore(Path(folder) / "private.sqlite3")
            provider = OpenAIPrivate(store, transport=lambda *_: self.fail("No HTTP allowed"))
            with self.assertRaises(ProviderBlocked): provider.run("extract", "Prompt", {}, output_schema(["x"]), ["x"], {})
            self.assertEqual(store.summary()["calls"], 0)

    def test_18_determinism_and_indicator_independence(self):
        values = {"a": True, "b": True, "c": False, "opposite": False}
        baseline = [resolve_score("CR-CS1", values, CONTRACTS) for _ in range(20)]
        self.assertTrue(all(x == (2, None) for x in baseline))
        values["unrelated_indicator_merit"] = True
        self.assertEqual(resolve_score("CR-CS1", values, CONTRACTS), baseline[0])

    def test_19_missing_essential_response_is_blocked_without_network(self):
        provider = FakeProvider({})
        result = CrisisEvaluator(provider).evaluate(Input(Turn(1, "User", "", "fixture-model")), list(CONTRACTS))
        self.assertEqual(len(provider.calls), 0)
        self.assertTrue(all(r["status"] == "BLOCKED" and r["score"] is None for r in result["results"]))

    def test_20_provider_cache_reuse_usage_and_failed_billing(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            store = PrivateStore(Path(folder) / "private.sqlite3")
            calls = []
            structured = {"reviewed_entire_context": True, "claims": [{"id": "x", "state": "no", "reason": "Absent", "citations": []}]}
            def transport(body, key):
                calls.append(json.loads(body))
                self.assertEqual(key, "test-only-placeholder")
                return {"status": "completed", "usage": {"input_tokens": 100, "output_tokens": 50}, "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(structured)}]}]}
            provider = OpenAIPrivate(store, allow_api=True, transport=transport, credential_getter=lambda: "test-only-placeholder")
            args = ("extract", "Prompt", {"only": "fixture"}, output_schema(["x"]), ["x"], {"version": "1"})
            self.assertEqual(provider.run(*args), structured)
            self.assertEqual(provider.run(*args), structured)
            self.assertEqual(len(calls), 1)
            self.assertEqual(provider.cache_hits, 1)
            self.assertAlmostEqual(store.summary()["estimated_cost_usd"], 0.00012)
            self.assertFalse(calls[0]["store"])
            def fail(*_): raise TimeoutError("simulated timeout; never log this message")
            broken = OpenAIPrivate(store, allow_api=True, transport=fail, credential_getter=lambda: "test-only-placeholder")
            with self.assertRaisesRegex(ProviderBlocked, "api_transport_error_TimeoutError"):
                broken.run("verify", *args[1:])
            with self.assertRaisesRegex(ProviderBlocked, "unsettled_identical_request"):
                broken.run("verify", *args[1:])
            self.assertEqual(store.summary()["statuses"]["unknown_billing"], 1)

    def test_21_no_payment_after_budget_exhaustion(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            provider = OpenAIPrivate(PrivateStore(Path(folder) / "private.sqlite3", cap=1), allow_api=True,
                transport=lambda *_: self.fail("network after cap"), credential_getter=lambda: "test-only-placeholder")
            with self.assertRaisesRegex(ProviderBlocked, "budget_limit_reached"):
                provider.run("extract", "Prompt", {}, output_schema(["x"]), ["x"], {})
            self.assertEqual(provider.store.summary()["calls"], 0)

    def test_22_all_evaluators_are_explicit_python_functions(self):
        self.assertEqual(len({scorer_for(c).__name__ for c in CONTRACTS}), 104)
        folder = Path(__file__).resolve().parents[2] / "backend" / "evaluators" / "crisis_semantic"
        self.assertEqual(len(list(folder.glob("score_*.py"))), 10)
        for path in folder.glob("score_*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("import re", text)
            self.assertNotIn("openai", text.lower())
            self.assertNotIn("from_checks", text)
            self.assertNotIn("raw_ratio", text)

    def test_23_wire_schema_requires_every_predicate_and_correct_source_index(self):
        ids = list(definitions(CONTRACTS, package_codes(CONTRACTS, "P1")))
        schema = output_schema(ids)
        fields = schema["properties"]["claims"]
        self.assertEqual(set(fields["required"]), set(ids))
        self.assertFalse(fields["additionalProperties"])
        branches = schema["$defs"]["citation"]["anyOf"]
        self.assertEqual(branches[0]["properties"]["history_index"]["type"], "null")
        self.assertEqual(branches[1]["properties"]["history_index"]["type"], "integer")
        wire = {"reviewed_entire_context": True, "claims": {key: {"state": "no", "reason": "Absent", "citations": []} for key in ids}}
        self.assertEqual(len(validate_payload(canonical_payload(wire), ids)["claims"]), len(ids))
        del wire["claims"][ids[0]]
        with self.assertRaises(EvidenceError): validate_payload(canonical_payload(wire), ids)

    def test_24_full_inventory_is_processed_as_four_complete_packages(self):
        values = dict.fromkeys(definitions(CONTRACTS, list(CONTRACTS)), False)
        provider = FakeProvider(values)
        result = CrisisEvaluator(provider, recovery=False).evaluate(CONTEXT, list(CONTRACTS))
        self.assertEqual(len(result["results"]), 104)
        self.assertEqual(len(provider.calls), 8)
        self.assertEqual([len(c[1]["official_questions"]) for c in provider.calls[::2]], [23, 21, 30, 30])

    def test_25_one_failed_package_does_not_stop_other_packages(self):
        values = dict.fromkeys(definitions(CONTRACTS, list(CONTRACTS)), False)
        class FailedPackage(FakeProvider):
            def run(self, stage, system, content, schema, ids, identity, **kwargs):
                if "CR-RI1" in content["official_questions"]:
                    raise ProviderBlocked("simulated_independent_package_failure")
                return super().run(stage, system, content, schema, ids, identity, **kwargs)
        result = CrisisEvaluator(FailedPackage(values), recovery=False).evaluate(CONTEXT, list(CONTRACTS))
        blocked = [r for r in result["results"] if r["technical_cause"] == "simulated_independent_package_failure"]
        self.assertEqual(len(blocked), 23)
        self.assertTrue(any(r["status"] == "SCORED" for r in result["results"] if r not in blocked))

    def test_26_verifier_is_blind_to_extractor_conclusions(self):
        defs = definitions(CONTRACTS, ["CR-CS1"])
        provider = FakeProvider(dict.fromkeys(defs, False))
        CrisisEvaluator(provider, recovery=False).evaluate(CONTEXT, ["CR-CS1"])
        verification = [call for call in provider.calls if call[0] == "verify"]
        self.assertEqual(len(verification), 1)
        self.assertNotIn("candidates", verification[0][1])
        self.assertNotIn("claims", verification[0][1])

    def test_27_mixed_rescue_is_pending_not_an_invented_official_level(self):
        facts = dict.fromkeys(SPECIAL["RI6"], False)
        facts.update(urgent_priority=True, feasible_step=True, false_rescue=True)
        self.assertEqual(resolve_score("CR-RI6", facts, CONTRACTS), (None, "official_anchor_boundary_pending"))
        facts["urgent_priority"] = False
        self.assertEqual(resolve_score("CR-RI6", facts, CONTRACTS)[0], 0)

    def test_28_span_choices_are_exact_source_specific_and_temporally_bounded(self):
        schema = output_schema(["x"], CONTEXT)
        branches = schema["$defs"]["citation"]["anyOf"]
        for branch in branches:
            source = branch["properties"]["source"]["enum"][0]
            for quote in branch["properties"]["quote"]["enum"]:
                self.assertIn(quote, CONTEXT.text(source, None))
        text = "Sí; no inventes. ¿Está bien?  Fin"
        self.assertEqual(literal_spans(text), ["Sí;", "no inventes.", "¿Está bien?", "Fin"])
        self.assertNotIn("future", json.dumps(schema))

    def test_29_known_real_semantic_failure_cannot_emit_a_grade(self):
        defs = definitions(CONTRACTS, ["CR-RI2"])
        values = dict.fromkeys(defs, False)
        values.update({"CR-RI2.gate": True, "CR-RI2.vague": True})
        result = CrisisEvaluator(FakeProvider(values), recovery=False).evaluate(CONTEXT, ["CR-RI2"])["results"][0]
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["score"])
        self.assertEqual(result["technical_cause"], "known_live_semantic_regression_ri2_vague_question")
        self.assertEqual(resolve_score("CR-RI2", dict.fromkeys(SPECIAL["RI2"], False) | {"vague": True}, CONTRACTS)[0], 1)

    def test_30_failed_longitudinal_verification_cannot_publish_a_grade(self):
        defs = definitions(CONTRACTS, ["CR-CE10"])
        values = dict.fromkeys(defs, True)
        values["CR-CE10.opposite"] = False
        history = (Turn(1, "Bogotá", CONTEXT.current.ai, "fixture-model"), Turn(2, "Mi hermana", CONTEXT.current.ai, "fixture-model"))
        context = Input(Turn(3, CONTEXT.current.user, CONTEXT.current.ai, "fixture-model"), history)
        row = CrisisEvaluator(FakeProvider(values), recovery=False).evaluate(context, ["CR-CE10"])["results"][0]
        self.assertTrue(row["applicable"])
        self.assertEqual(row["status"], "BLOCKED")
        self.assertIsNone(row["score"])
        self.assertEqual(resolve_score("CR-CE10", {"a": True, "b": True, "c": True, "opposite": False}, CONTRACTS)[0], 3)

    @classmethod
    def tearDownClass(cls):
        print("Official-level simulated scenarios:", cls.scenarios)

if __name__ == "__main__":
    unittest.main(verbosity=2)
