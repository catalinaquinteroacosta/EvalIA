"""Standard-library Responses API, isolated cache and additional US$10 grant.

Only OPENAI_API_KEY inherited by the process is used. No credential files are read.
There are no automatic HTTP retries. Unknown billing retains the full reservation.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import sqlite3
import socket
import time
import urllib.request
import urllib.error
from .domain import PRIVATE, digest
from .evidence import validate_payload, canonical_payload, EvidenceError

MODEL = "gpt-4.1-mini-2025-04-14"
AUTHORIZATION_BASELINE_NANODOLLARS = 6_379_310_800
ADDITIONAL_AUTHORIZED_NANODOLLARS = 10_000_000_000
# Existing uncertain reservations count against this ceiling as well.
MAX_NANODOLLARS = AUTHORIZATION_BASELINE_NANODOLLARS + ADDITIONAL_AUTHORIZED_NANODOLLARS
# Official standard text prices: US$0.40 input / US$1.60 output per million.
INPUT_NANODOLLARS = 400
OUTPUT_NANODOLLARS = 1600
PRICE_SOURCE = "https://developers.openai.com/api/docs/models/gpt-4.1-mini"
MODEL_RATES = {MODEL: (400, 1600), "gpt-4.1-2025-04-14": (2000, 8000)}

class ProviderBlocked(RuntimeError):
    pass

class PrivateStore:
    def __init__(self, path=None, cap=MAX_NANODOLLARS):
        self.path = Path(path) if path else PRIVATE / "crisis_private.sqlite3"
        self.path = self.path.resolve()
        allowed = Path(__file__).resolve().parent
        test_allowed = allowed.parents[2] / "tests" / "crisis_semantic"
        if not (self.path.is_relative_to(allowed) or self.path.is_relative_to(test_allowed)):
            raise ValueError("private_store_must_be_inside_isolated_crisis_folders")
        if type(cap) is not int or not 0 <= cap <= MAX_NANODOLLARS:
            raise ValueError("budget_above_user_authorization")
        self.cap = cap
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, stage TEXT NOT NULL,
              cache_key TEXT NOT NULL, reserved INTEGER NOT NULL, committed INTEGER NOT NULL,
              actual INTEGER, input_tokens INTEGER, output_tokens INTEGER,
              status TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS call_rates (call_id INTEGER PRIMARY KEY,
              model TEXT NOT NULL, input_rate INTEGER NOT NULL, output_rate INTEGER NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def cached(self, key):
        with self.connect() as db:
            row = db.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def reserve(self, key, stage, amount, model=MODEL):
        if type(amount) is not int or amount <= 0:
            raise ValueError("invalid_reservation")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # A repeated request with indeterminate billing is not automatically sent again.
            previous = db.execute("SELECT status FROM calls WHERE cache_key=? AND status IN ('reserved','unknown_billing')", (key,)).fetchone()
            if previous:
                raise ProviderBlocked("unsettled_identical_request")
            used = db.execute("SELECT COALESCE(SUM(committed),0) FROM calls").fetchone()[0]
            if used + amount > self.cap:
                raise ProviderBlocked("budget_limit_reached")
            cursor = db.execute("INSERT INTO calls(stage,cache_key,reserved,committed,status,created) VALUES(?,?,?,?,?,?)", (stage, key, amount, amount, "reserved", time.time()))
            db.execute("INSERT INTO call_rates VALUES(?,?,?,?)", (cursor.lastrowid, model, *MODEL_RATES[model]))
            return cursor.lastrowid

    def settle(self, call, usage, status):
        actual, inp, out = None, None, None
        if isinstance(usage, dict):
            inp, out = usage.get("input_tokens"), usage.get("output_tokens")
            if type(inp) is int and type(out) is int and inp >= 0 and out >= 0:
                with self.connect() as rates_db:
                    rates = rates_db.execute("SELECT input_rate,output_rate FROM call_rates WHERE call_id=?", (call,)).fetchone() or (INPUT_NANODOLLARS, OUTPUT_NANODOLLARS)
                actual = inp * rates[0] + out * rates[1]
        with self.connect() as db:
            reserved = db.execute("SELECT reserved FROM calls WHERE id=?", (call,)).fetchone()[0]
            if actual is not None and actual > reserved:
                # Stop subsequent calls: a pricing/token-bound discrepancy must not be hidden.
                db.execute("UPDATE calls SET committed=?,actual=?,input_tokens=?,output_tokens=?,status='pricing_bound_violation' WHERE id=?", (MAX_NANODOLLARS, actual, inp, out, call))
            else:
                db.execute("UPDATE calls SET committed=?,actual=?,input_tokens=?,output_tokens=?,status=? WHERE id=?", (actual if actual is not None else reserved, actual, inp, out, status if actual is not None else "unknown_billing", call))

    def put(self, key, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO cache VALUES(?,?)", (key, json.dumps(value, ensure_ascii=False)))

    def summary(self):
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*),COALESCE(SUM(actual),0),COALESCE(SUM(committed),0),COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0) FROM calls").fetchone()
            states = dict(db.execute("SELECT status,COUNT(*) FROM calls GROUP BY status").fetchall())
            hits = db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            models = dict(db.execute("SELECT COALESCE(r.model,?),COUNT(*) FROM calls c LEFT JOIN call_rates r ON r.call_id=c.id GROUP BY COALESCE(r.model,?)", (MODEL, MODEL)).fetchall())
        return {"model": MODEL, "models": models, "calls": row[0], "estimated_cost_usd": row[1] / 1e9,
                "committed_upper_bound_usd": row[2] / 1e9, "input_tokens": row[3], "output_tokens": row[4],
                "cap_usd": self.cap / 1e9, "statuses": states, "cache_entries": hits,
                "price_source": PRICE_SOURCE,
                "model_rates_usd_per_million": {name: {"input": rates[0] / 1000, "output": rates[1] / 1000} for name, rates in MODEL_RATES.items()},
                "price_sources": [PRICE_SOURCE, "https://developers.openai.com/api/docs/models/gpt-4.1"],
                "pricing_verified_client_date": "2026-10-11"}

class OpenAIPrivate:
    def __init__(self, store=None, *, allow_api=False, transport=None, timeout=180, credential_getter=None, model=MODEL):
        if model not in MODEL_RATES:
            raise ValueError("model_rate_not_verified")
        self.model = model
        self.store = store or PrivateStore()
        self.allow_api = allow_api
        self.transport = transport or self._transport
        self.timeout = timeout
        self.credential_getter = credential_getter or (lambda: os.environ.get("OPENAI_API_KEY"))
        self.cache_hits = 0

    def _transport(self, body, key):
        request = urllib.request.Request("https://api.openai.com/v1/responses", data=body,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.load(response)

    def run(self, stage, system, content, schema, ids, identity, max_output_tokens=20000):
        payload = {"model": self.model, "store": False, "temperature": 0,
                   "max_output_tokens": max_output_tokens,
                   "input": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(content, ensure_ascii=False)}],
                   "text": {"format": {"type": "json_schema", "name": "crisis_observations", "strict": True, "schema": schema}}}
        cache_key = digest({"request": payload, "identity": identity, "stage": stage})
        cached = self.store.cached(cache_key)
        if cached is not None:
            validate_payload(cached, ids)
            self.cache_hits += 1
            return cached
        if not self.allow_api:
            with self.store.connect() as db:
                pending = db.execute("SELECT 1 FROM calls WHERE cache_key=? AND status IN ('reserved','unknown_billing')", (cache_key,)).fetchone()
            if pending:
                raise ProviderBlocked("unsettled_identical_request")
            raise ProviderBlocked("real_api_not_enabled")
        credential = self.credential_getter()
        if not credential:
            raise ProviderBlocked("secure_process_configuration_missing")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        # Bytes are an overestimate of BPE tokens. Double serialized bytes plus
        # 8192 tokens bounds framing/schema overhead conservatively; no tools.
        input_rate, output_rate = MODEL_RATES[self.model]
        reserve = (2 * len(body) + 8192) * input_rate + max_output_tokens * output_rate
        call = self.store.reserve(cache_key, stage, reserve, self.model)
        try:
            response = self.transport(body, credential)
        except BaseException as error:
            underlying = getattr(error, "reason", error)
            definitely_not_sent = isinstance(underlying, (socket.gaierror, PermissionError)) or getattr(underlying, "winerror", None) == 10013
            self.store.settle(call, {"input_tokens": 0, "output_tokens": 0} if definitely_not_sent else None,
                              "not_sent" if definitely_not_sent else "transport_error")
            # No raw exception/headers/body/credential is surfaced or persisted.
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            diagnostic = "api_transport_error_" + type(error).__name__ + "_" + type(underlying).__name__
            code = getattr(underlying, "winerror", None) or getattr(underlying, "errno", None)
            if type(code) is int: diagnostic += "_code_" + str(code)
            raise ProviderBlocked(diagnostic) from None
        self.store.settle(call, response.get("usage"), response.get("status", "unknown"))
        if response.get("status") != "completed":
            raise ProviderBlocked("api_response_not_completed")
        parts = [c.get("text", "") for item in response.get("output", []) if item.get("type") == "message" for c in item.get("content", []) if c.get("type") == "output_text"]
        try:
            wire = json.loads("".join(parts))
            if identity.get("protocol") == "span-observations-2":
                from .span_protocol import decode
                parsed = decode(wire, content["literal_spans"], content["predicates"])
            elif identity.get("audit_protocol") == "closure-assertion-truth-4":
                mapping = {"supported":"yes","contradicted":"no","undetermined":"unknown"}
                parsed = {"reviewed_entire_context":wire["reviewed_entire_context"],"claims":[{"id":key,"state":mapping[value["truth"]],"citations":value["citations"],"reason":value["reason"]} for key,value in wire["claims"].items()]}
            else:
                parsed = canonical_payload(wire)
            validate_payload(parsed, ids)
        except (ValueError, TypeError, KeyError) as error:
            cause = str(error) if isinstance(error, EvidenceError) else type(error).__name__
            diagnostic = {"stage": stage, "cause": cause, "output_text": "".join(parts)}
            self.store.path.with_name("rejected_" + cache_key + ".json").write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
            raise ProviderBlocked("api_structured_output_invalid_" + cause) from None
        self.store.put(cache_key, parsed)
        return parsed
