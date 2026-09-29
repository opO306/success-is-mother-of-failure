"""C1-B1 Proof Cache V0: a shelf of verified point witnesses, re-verified from their bytes on every use.

Contract: docs/active/C1B1_PROOF_CACHE_V0.md, designer verdicts Q-PC1..Q-PC4 (2026-09-30) and Runtime Rounding Contract V1
sections 5 and 7. A proof store, not a compute cache: it is asked only when the executor STOPS, and it can only turn that
STOP into a witness that the V2 checker accepts again, right now, from the stored bytes.

Shelf layout (one local append-only shelf, single writer; the formal one is runs/c1b1_proof_cache_v0/):
    shelf.json      {"format", "kind"}: kind is "production" or "test_only", fixed at creation
    objects/<sha>   the canonical witness bytes (certificate + runtime binding), exactly as verified; name = SHA-256
    index.jsonl     exact lookup key -> content address, nothing else
    events.jsonl    admission metadata (cap, schedule, production STOP, run id, time, host, prover summary) and every
                    use result (hit / stale / rejected / refused)
Both logs are hash chains of canonical JSON lines, and every index line's hash is also written into its admit event; a
broken chain or a missing cross-reference makes the whole shelf unusable (no lookup, no admission). Limit: a chain cannot
see an edit of the LAST events line (nothing points to it yet). Safety does not rest on the logs: every stored witness is
re-verified from its bytes before use, so a forged log can cost availability or revive a dead entry for a re-check, never
put an unverified raw into the world. Nothing is ever deleted or overwritten.

Use results (verdict Q-PC3):
    hit       verify_witness passed: the raw is used
    STALE     the stored binding differs from the current one: kept, never used again
    REJECTED  address mismatch / missing or malformed object / input mismatch / checker INVALID: kept, never used again,
              never revived
    REFUSED   checker REFUSED or the byte limit: NOT a falsity. Only this use fails; the entry stays usable

Admission (verdict Q-PC2): this module, not the wrapper, is the admission layer. It reads the executor's precision cap
around the step. A production shelf admits only witnesses the prover made for a STOP at the production cap 16384; a
test_only shelf admits any (cap-128 rehearsal tests). The precision schedule is admission metadata, never binding.
"""
import hashlib
import json
import os
import platform
import time
from pathlib import Path

import a_reference.c1b1_runtime_wrapper as RW
import a_reference.c1b1_two_atom as C

FORMAT = "c1b1-proof-cache-v0"
PRODUCTION, TEST_ONLY = "production", "test_only"
PRODUCTION_CAP = 16384
HIT, STALE, REJECTED, REFUSED = "hit", "STALE", "REJECTED", "REFUSED"
GENESIS = "0" * 64


def canonical(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def key_doc(key, run):
    """The exact lookup key of a STOP: the mathematical binding (by digest) and the exact impulse input."""
    return {"binding_sha256": _sha(canonical(RW.binding(run))),
            "input": {"dr_raw": [str(v) for v in RW._dr_raw(key[0])], "component": key[1], "dt_kick": str(key[2])}}


def classify(reason):
    """Q-PC3: a verify_witness rejection reason -> STALE / REJECTED / REFUSED."""
    if reason == "stale_binding":
        return STALE
    if reason.startswith("checker_refused:") or reason == "certificate_too_large":
        return REFUSED
    return REJECTED


class _Chain:
    """An append-only hash-chained JSON-lines log. verify() checks every line; append() extends it."""

    def __init__(self, path):
        self.path, self.records, self.line_sha, self.head = path, [], [], GENESIS

    def load(self):
        if not self.path.exists():
            return
        for n, line in enumerate(self.path.read_bytes().split(b"\n")[:-1]):
            rec = json.loads(line)
            if not isinstance(rec, dict) or rec.get("seq") != n or rec.get("prev") != self.head or canonical(rec) != line:
                raise ValueError(f"{self.path.name}: line {n} breaks the chain")
            self.records.append(rec)
            self.head = _sha(line)
            self.line_sha.append(self.head)
        if self.path.read_bytes()[-1:] not in (b"", b"\n"):
            raise ValueError(f"{self.path.name}: truncated last line")

    def append(self, body):
        rec = dict(body, seq=len(self.records), prev=self.head)
        line = canonical(rec)
        with open(self.path, "ab") as f:
            f.write(line + b"\n")
        self.records.append(rec)
        self.head = _sha(line)
        self.line_sha.append(self.head)
        return rec


class ProofCache:
    def __init__(self, root, kind, run_id=None):
        if kind not in (PRODUCTION, TEST_ONLY):
            raise ValueError(f"unknown shelf kind {kind!r}")
        self.root, self.kind, self.run_id = Path(root), kind, run_id
        (self.root / "objects").mkdir(parents=True, exist_ok=True)
        marker = self.root / "shelf.json"
        want = {"format": FORMAT, "kind": kind}
        if marker.exists():
            if json.loads(marker.read_bytes()) != want:
                raise ValueError(f"shelf {self.root} is not a {kind} {FORMAT} shelf")
        else:
            marker.write_bytes(canonical(want))
        self.index, self.events = _Chain(self.root / "index.jsonl"), _Chain(self.root / "events.jsonl")
        self.corrupt = None
        try:
            self.index.load()
            self.events.load()
            anchored = {(ev.get("index_seq"), ev.get("index_line_sha256"))
                        for ev in self.events.records if ev.get("event") == "admit"}
            for rec, h in zip(self.index.records, self.index.line_sha):
                if (rec["seq"], h) not in anchored:
                    raise ValueError(f"index.jsonl: line {rec['seq']} has no matching admit event")
        except (ValueError, json.JSONDecodeError) as e:
            self.corrupt = str(e)
        self.dead = {}                                                  # index seq -> STALE / REJECTED (sticky)
        for ev in self.events.records:
            if ev.get("event") == "use" and ev.get("result") in (STALE, REJECTED):
                self.dead.setdefault(ev["index_seq"], ev["result"])

    # --- read side (called by the wrapper at a STOP) ------------------------------------------------------------------

    def lookup(self, key, run, config):
        """(raw, witness record) for a STOP, or None. Every candidate is re-verified from its bytes; nothing is trusted."""
        if self.corrupt is not None or RW._dr_raw(key[0]) is None:
            return None
        doc = key_doc(key, run)
        kid = _sha(canonical(doc))
        for entry in reversed(self.index.records):
            if entry["key_id"] != kid or entry["seq"] in self.dead:
                continue
            result, reason, raw, data = self._check(entry, key, run, config)
            self.events.append({"event": "use", "index_seq": entry["seq"], "address": entry["address"],
                                "result": result, "reason": reason, "run_id": self.run_id})
            if result in (STALE, REJECTED):
                self.dead[entry["seq"]] = result
            if result == HIT:
                return raw, RW.witness_record(key, raw, data, "cache", cache={"kind": self.kind, "index_seq": entry["seq"]})
        return None

    def _check(self, entry, key, run, config):
        path = self.root / "objects" / entry["address"]
        if not path.is_file():
            return REJECTED, "missing_object", None, None
        data = path.read_bytes()
        if _sha(data) != entry["address"]:
            return REJECTED, "address_mismatch", None, None
        try:
            raw = RW.verify_witness(data, key, run, None, config)
        except RW._Reject as r:
            return classify(r.reason), r.reason, None, None
        return HIT, "valid", raw, data

    # --- admission side (the caller's layer; never the wrapper) -------------------------------------------------------

    def admit(self, key, run, data, admission, prover=None):
        """Store bytes the wrapper verified and index them under the exact key. Returns the index record or None."""
        if self.corrupt is not None:
            return None
        address = _sha(data)
        why = self._admission_refusal(admission)
        if why is not None:
            self.events.append({"event": "admission_refused", "address": address, "reason": why,
                                "admission": admission, "run_id": self.run_id})
            return None
        path = self.root / "objects" / address
        if path.exists():
            if path.read_bytes() != data:                               # never overwrite, even a damaged object
                self.events.append({"event": "admission_refused", "address": address, "reason": "object_conflict",
                                    "admission": admission, "run_id": self.run_id})
                return None
        else:
            tmp = path.with_name(address + ".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, path)
        doc = key_doc(key, run)
        kid = _sha(canonical(doc))
        existing = [e for e in self.index.records
                    if e["key_id"] == kid and e["address"] == address and e["seq"] not in self.dead]
        entry = existing[-1] if existing else self.index.append({"key_id": kid, "key": doc, "address": address})
        self.events.append({"event": "admit", "index_seq": entry["seq"], "address": address, "admission": admission,
                            "index_line_sha256": self.index.line_sha[entry["seq"]],
                            "prover": prover, "run_id": self.run_id, "new_index_entry": not existing})
        return entry

    def _admission_refusal(self, admission):
        if self.kind == TEST_ONLY:
            return None
        if admission.get("kind") != PRODUCTION:
            return "not_production_admission"
        if not (admission.get("cap_before") == admission.get("cap_after") == PRODUCTION_CAP):
            return "not_production_cap"
        if admission.get("production_stop") is not True:
            return "not_a_production_stop"
        return None

    def status(self, run=None):
        """A report: entries per state. With a run, entries bound to another binding are counted as STALE."""
        cur = _sha(canonical(RW.binding(run))) if run is not None else None
        out = {"corrupt": self.corrupt, "entries": len(self.index.records), STALE: 0, REJECTED: 0, "usable": 0}
        for e in self.index.records:
            state = self.dead.get(e["seq"])
            if state is None and cur is not None and e["key"]["binding_sha256"] != cur:
                state = STALE
            out[state or "usable"] += 1
        return out


def _admission(kind, cap_before, cap_after):
    schedule, m = [], C.START_PRECISION_BITS
    while m <= cap_before:
        schedule.append(m)
        m *= 2
    return {"kind": kind, "cap_before": cap_before, "cap_after": cap_after, "schedule": schedule,
            "production_stop": cap_before == cap_after == PRODUCTION_CAP,
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": platform.node()}


def step(run, cache, config=None):
    """The admission layer: one wrapper step with cache lookups, then admission of the witnesses the prover made.

    The cap is read here, around the step, and never by the wrapper. A production shelf admits only when it was the
    production cap throughout; the wrapper's verdict on the step does not depend on the cache at all."""
    config = config or RW.Config()
    cfg = RW.Config(config.budget, config.limits, config.max_certificate_bytes, config.max_attempts_per_step, cache)
    cap_before = C.MAX_PRECISION_BITS
    outcome = RW.step(run, cfg)
    cap_after = C.MAX_PRECISION_BITS
    if outcome.advanced and outcome.new_certificates:
        admission = _admission(PRODUCTION if cache.kind == PRODUCTION else TEST_ONLY, cap_before, cap_after)
        summaries = {w["certificate_sha256"]: w["prover"] for w in outcome.witnesses if w["source"] == "prover"}
        for key, data in outcome.new_certificates:
            cache.admit(key, run, data, admission, prover=summaries.get(_sha(data)))
    return outcome


def run_steps(run, n, cache, config=None):
    out = []
    for _ in range(n):
        o = step(run, cache, config)
        out.append(o)
        if not o.advanced:
            break
    return out
