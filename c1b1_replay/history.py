"""Small C1-B1 commit gate, not a world rollback engine. No automatic retry."""
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
from . import exact, spec
from .provenance import fingerprints
from .types import Limits, Refused, Verdict
from .verify import verify
from .witness import Reader

@dataclass(frozen=True)
class Approval:
    designer_decision: str
    spec_fingerprint: str
    implementation_fingerprint: str
    dependency_fingerprint: str

    def matches(self):
        implementation,dependency=fingerprints()
        return bool(self.designer_decision.strip()) and (
            self.spec_fingerprint,self.implementation_fingerprint,self.dependency_fingerprint
        )==(spec.SPEC_FINGERPRINT,implementation,dependency)

@dataclass(frozen=True)
class Entry:
    witness_path: Path
    sha256: str
    header: object
    status: str = "SPECULATIVE"
    evidence: str = "EXECUTED"
    result: object = None

class History:
    def __init__(self,store,origin,*,origin_step=0,approval=None,limits=None):
        self.store=Path(store)
        self.store.mkdir(parents=True,exist_ok=True)
        self.confirmed=exact.state(origin)
        if type(origin_step) is not int or origin_step<0:
            raise ValueError("origin_step")
        self.confirmed_step=origin_step
        self.approval=approval
        self.limits=limits or Limits()
        self.entries=[]
        self.halted=False

    def enqueue(self,witness):
        if self.halted:
            raise Refused("history halted; no automatic rerun")
        if not isinstance(witness,bytes):
            raise TypeError("immutable witness bytes required")
        if len(witness)>self.limits.max_bytes:
            raise Refused("retained witness byte cap")
        header=Reader(io.BytesIO(witness),self.limits).header()
        pending=[e for e in self.entries if e.status=="SPECULATIVE"]
        if sum(e.header.n_steps for e in pending)+header.n_steps>self.limits.max_steps:
            raise Refused("speculative distance cap")
        if sum(e.witness_path.stat().st_size for e in pending)+len(witness)>self.limits.max_bytes:
            raise Refused("speculative storage cap")
        digest=hashlib.sha256(witness).hexdigest()
        path=self.store/(digest+".c1br")
        if path.exists():
            if path.read_bytes()!=witness:
                raise Refused("retained witness identity mismatch")
        else:
            with path.open("xb") as stream:
                stream.write(witness)
        entry=Entry(path,digest,header)
        self.entries.append(entry)
        return entry

    def verify_next(self):
        from dataclasses import replace
        if self.halted:
            raise Refused("history halted; investigate before explicit recovery")
        index=next((i for i,e in enumerate(self.entries) if e.status=="SPECULATIVE"),None)
        if index is None:
            raise Refused("no speculative interval")
        entry=self.entries[index]
        result=verify(entry.witness_path,self.limits)
        if result.verdict==Verdict.VALID and (
            entry.header.initial!=self.confirmed or entry.header.start_step!=self.confirmed_step or
            result.witness_sha256!=entry.sha256):
            result=replace(result,verdict=Verdict.INVALID,reason="history origin/retained witness binding mismatch")
        if result.verdict==Verdict.INVALID:
            for i in range(index,len(self.entries)):
                self.entries[i]=replace(self.entries[i],status="DISCARDED",result=result if i==index else None)
            self.halted=True
        elif result.verdict==Verdict.REFUSED:
            self.entries[index]=replace(entry,result=result)
            self.halted=True
        elif self.approval is None or not self.approval.matches():
            self.entries[index]=replace(entry,result=result)
            self.halted=True
        else:
            self.entries[index]=replace(entry,status="CONFIRMED",evidence="REPLAY_VERIFIED",result=result)
            self.confirmed=result.last_state
            self.confirmed_step+=entry.header.n_steps
        return result
