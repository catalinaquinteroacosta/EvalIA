"""Source isolation, longitudinal audit, mixed-model budget and joint packages."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend/evaluators"))
from crisis_semantic.domain import Turn, Input, load_contracts, package_codes, PACKAGES
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.evidence import EvidenceError, validate_payload, literal_check
from crisis_semantic.span_protocol import spans, schema, decode
from crisis_semantic.openai_private import PrivateStore, OpenAIPrivate, ProviderBlocked, MAX_NANODOLLARS
from crisis_semantic.span_provider import SpanProvider, fingerprint
from crisis_semantic.scoring import resolve_score
from crisis_semantic.pipeline import EXTRACT

class Step8Tests(unittest.TestCase):
    def setUp(self):
        self.contracts, _, _ = load_contracts()
        self.context = Input(Turn(3,"Sigo en Bogotá.","Sigues en Madrid sin apoyo.","test"), (Turn(1,"Vivo en Bogotá.","Estás en Bogotá.","test"),Turn(2,"Mi hermana me escucha.","Tu hermana te escucha.","test")))

    def test_all_four_packages_have_source_constrained_schema(self):
        library = spans(self.context)
        for package in PACKAGES:
            defs = definitions(self.contracts, package_codes(self.contracts, package))
            wire_schema = schema(defs, library)
            self.assertEqual(set(wire_schema["properties"]["claims"]["required"]), set(defs))
            response = wire_schema["$defs"]["response"]["anyOf"][0]
            self.assertEqual(response["properties"]["evidence"]["minItems"], 1)
            self.assertTrue(all(library[key]["source"] == "current_ai" for key in response["properties"]["evidence"]["items"]["enum"]))

    def test_decoder_rejects_user_as_ai_evidence_and_fabricated_references(self):
        defs = definitions(self.contracts, ["CR-AC3", "CR-AC4", "CR-RE4"])
        library = spans(self.context)
        ai = next(k for k,v in library.items() if v["source"] == "current_ai")
        user = next(k for k,v in library.items() if v["source"] == "current_user")
        wire = {"reviewed_entire_context": True, "claims": {k:{"observation":"present","evidence":[ai],"context":[user],"reason":"Fixture only"} for k in defs}}
        self.assertEqual(len(validate_payload(decode(wire,library,defs),defs)["claims"]),len(defs))
        for invalid in (user, "invented_span"):
            mutated = json.loads(json.dumps(wire))
            mutated["claims"][next(iter(defs))]["evidence"] = [invalid]
            with self.assertRaises(EvidenceError): decode(mutated,library,defs)

    def test_positive_requires_support_even_with_full_review(self):
        defs = definitions(self.contracts,["CR-CS1"])
        wire = {"reviewed_entire_context":True,"claims":{k:{"observation":"present","evidence":[],"context":[],"reason":"Bad positive"} for k in defs}}
        with self.assertRaises(EvidenceError): decode(wire,spans(self.context),defs)

    def test_longitudinal_support_requires_actual_prior_quote(self):
        defs = definitions(self.contracts,["CR-CE10"])
        key = "CR-CE10.opposite"
        claim = {"id":key,"state":"yes","reason":"Contradiction","citations":[{"source":"current_ai","history_index":None,"quote":self.context.current.ai}]}
        self.assertIn("longitudinal_context_not_evidenced", literal_check(claim,defs[key],self.context,True,()))
        claim["citations"].append({"source":"prior_user","history_index":0,"quote":"Vivo en Bogotá."})
        self.assertEqual(literal_check(claim,defs[key],self.context,True,()),[])

    def test_mixed_model_costs_do_not_reprice_historical_calls(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            store = PrivateStore(Path(directory)/"cost.sqlite3")
            mini = store.reserve("mini","extract",1000000)
            store.settle(mini,{"input_tokens":100,"output_tokens":50},"completed")
            full = store.reserve("full","verify",1000000,"gpt-4.1-2025-04-14")
            store.settle(full,{"input_tokens":100,"output_tokens":50},"completed")
            self.assertAlmostEqual(store.summary()["estimated_cost_usd"],0.00072)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT actual FROM calls WHERE id=?",(mini,)).fetchone()[0],120000)

    def test_unknown_billing_is_retained_across_new_protocol_and_model(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            store = PrivateStore(Path(directory)/"cost.sqlite3",cap=1000)
            call = store.reserve("old","verify",900)
            store.settle(call,None,"timeout")
            with self.assertRaises(ProviderBlocked): store.reserve("new-protocol","verify",101,"gpt-4.1-2025-04-14")
            self.assertEqual(store.summary()["committed_upper_bound_usd"],900/1e9)
            with self.assertRaises(ProviderBlocked): store.reserve("old","verify",1)

    def test_unknown_model_cannot_spend_without_verified_rate(self):
        with self.assertRaises(ValueError): OpenAIPrivate(model="unpriced-model")

    def test_valid_cached_pair_is_reused_without_network_or_credentials(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            provider = SpanProvider(PrivateStore(Path(directory)/"cache.sqlite3"), credential_getter=lambda: self.fail("credentials read during valid reuse"))
            defs = definitions(self.contracts,["CR-CS1"])
            claim = lambda key: {"id":key,"state":"no","citations":[],"reason":"Simulated reviewed absence"}
            provider.seed = {key:{"value":False,"issues":[],"extraction":claim(key),"verification":claim(key)} for key in defs}
            content = {"conversation":self.context.payload(),"predicates":defs,"official_questions":{"CR-CS1":"Question"},"official_gates":{"CR-CS1":"General"},"external_attestations":[]}
            for stage in ("extract","verify"):
                actual = provider.run(stage,EXTRACT,content,{},list(defs),{})
                validate_payload(actual,defs)
            self.assertEqual(provider.store.summary()["calls"],0)
            self.assertEqual(provider.reused_observations,2*len(defs))

    def test_invalid_cached_source_never_becomes_a_verified_observation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            provider = SpanProvider(PrivateStore(Path(directory)/"cache.sqlite3"))
            defs = definitions(self.contracts,["CR-AC3"])
            bad = lambda key: {"id":key,"state":"yes","citations":[{"source":"current_user","history_index":None,"quote":self.context.current.user}],"reason":"Bad cached source"}
            provider.seed = {key:{"value":True,"issues":[],"extraction":bad(key),"verification":bad(key)} for key in defs}
            content = {"conversation":self.context.payload(),"predicates":defs,"official_questions":{"CR-AC3":"Question"},"official_gates":{"CR-AC3":"General"},"external_attestations":[]}
            with self.assertRaises(ProviderBlocked): provider.run("extract",EXTRACT,content,{},list(defs),{})
            self.assertEqual(provider.reused_observations,0)
            self.assertEqual(provider.store.summary()["calls"],0)

    def test_real_joint_battery_recomputes_scores_and_verifies_every_positive_quote(self):
        root = Path(__file__).resolve().parents[2]
        # Immutable step-8 baseline, not the closure protocol's new identity.
        path = root / "docs/crisis_semantic/step8/89ab272880c4/comparison_8660c0df2a.json"
        self.assertTrue(path.exists(), "Run the joint battery or its offline replay first")
        report = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(report["clinical_validation"])
        self.assertFalse(report["step9_started"])
        covered, comparable = set(), 0
        for batch in report["reports"]:
            raw = batch["context"]
            history = tuple(Turn(t["number"],t["user"],t["ai"],t["model"]) for t in raw["history"])
            context = Input(Turn(raw["current_turn"],raw["current_user"],raw["current_ai"],raw["model_evaluated"]),history)
            expected_codes = package_codes(self.contracts,batch["package"])
            self.assertEqual({r["code"] for r in batch["evaluation"]["results"]},set(expected_codes))
            defs = definitions(self.contracts,expected_codes)
            for row in batch["evaluation"]["results"]:
                if not batch["extra"]:
                    covered.add(row["code"])
                    comparable += 1
                for key,decision in row.get("verified_decisions",{}).items():
                    for stage in ("extraction","verification"):
                        claim = decision[stage]
                        if claim["state"] == "yes":
                            self.assertEqual(literal_check(claim,defs[key],context,True,()),[],(batch["case"],key,stage))
                if row["status"] == "SCORED":
                    facts = {k.split(".",1)[1]:v["value"] for k,v in row["verified_decisions"].items()}
                    score,cause = resolve_score(row["code"],facts,self.contracts)
                    self.assertEqual(row["score"],score,(batch["case"],row["code"]))
                    self.assertIsNone(cause)
                    self.assertEqual(row["official_descriptor"],self.contracts[row["code"]]["levels"][str(score)]["text"])
                else:
                    self.assertIsNone(row["score"])
        self.assertEqual(len(covered),104)
        self.assertEqual(comparable,501)
        self.assertEqual(report["after"]["checks_passed"],31)
        self.assertEqual(set(report["qualification"]["components"]),{"CR-RI2","CR-CE10"})
        self.assertEqual(len(report["qualification"]["components"]["CR-RI2"]),8)
        self.assertEqual({c["actual"] for c in report["qualification"]["components"]["CR-CE10"]},{0,3})

if __name__ == "__main__":
    unittest.main(verbosity=2)
