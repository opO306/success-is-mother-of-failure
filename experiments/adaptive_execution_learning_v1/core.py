"""Immutable JSON, raw seals and single-writer local journals, not OS isolation."""
from __future__ import annotations
import gzip
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "experiments/adaptive_execution_learning_v1"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def raw_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for key, val in items:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = val
        return result
    raw = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def write_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical(obj))
        stream.flush()
        os.fsync(stream.fileno())


def protocol():
    return read(HERE / "protocol.json")


def check_frozen():
    for relative, expected in read(HERE / "protocol_seal.json")["files"].items():
        if raw_hash(ROOT / relative) != expected:
            raise ValueError("PROTOCOL_INTEGRITY:" + relative)
    for relative, expected in read(HERE / "preservation_manifest.json")["files"].items():
        if raw_hash(ROOT / relative) != expected:
            raise ValueError("PROTECTED_SOURCE_INTEGRITY:" + relative)


def stopped(directory):
    return (Path(directory) / "STOP.json").exists()


def stop(directory, reason, evidence):
    path = Path(directory) / "STOP.json"
    if not path.exists():
        write_new(path, {"status": "STOP", "reason": reason, "evidence": evidence})


class Ledger:
    """Hash chaining catches modified interior records; tail deletion needs external witness."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def history(self):
        previous, result = "GENESIS", []
        for index, path in enumerate(sorted(self.directory.glob("event_*.json"))):
            obj = read(path)
            body = {key: val for key, val in obj.items() if key != "sha256"}
            if (path.name != f"event_{index:06d}.json" or body.get("index") != index
                    or body.get("previous") != previous or obj.get("sha256") != digest(body)
                    or path.read_bytes() != canonical(obj)):
                raise ValueError("LEDGER_INTEGRITY")
            previous = obj["sha256"]
            result.append(obj)
        return result

    def append(self, payload):
        # Linux-only run surface; persistent lock file is not removed/replaced.
        import fcntl
        with (self.directory / "writer.lock").open("ab") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError("CONCURRENT_WRITER_REFUSED") from error
            history = self.history()
            body = {"index": len(history), "previous": history[-1]["sha256"] if history else "GENESIS", "payload": payload}
            event = dict(body, sha256=digest(body))
            write_new(self.directory / f"event_{len(history):06d}.json", event)
            return event
