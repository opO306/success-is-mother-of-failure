"""Ordered all-step verification; the only trusted state advances after checks pass."""
import io
from pathlib import Path
import time
import mpmath
from . import exact, spec
from .model import Model
from .provenance import fingerprints, independence
from .types import Invalid, Limits, Refused, Result, Verdict
from .witness import Reader

class Budget:
    def __init__(self,limits,start):
        self.limits,self.start=limits,start
        self.evaluations=self.max_precision=0
    def check(self):
        if time.perf_counter()-self.start>self.limits.seconds:
            raise Refused("verification time cap")
    def evaluate(self,bits):
        self.check()
        if self.evaluations>=self.limits.max_evaluations:
            raise Refused("interval evaluation cap")
        self.evaluations+=1
        self.max_precision=max(self.max_precision,bits)

def verify(source,limits=None,*,materialize=False):
    """Path, bytes, or binary stream. materialize uses identical checks on bounded bytes."""
    limits=limits or Limits()
    start,cpu=time.perf_counter(),time.process_time()
    budget=Budget(limits,start)
    reader=None
    owned=None
    current=None
    steps=0
    implementation=dependency=""
    verdict,reason=Verdict.REFUSED,"not completed"
    try:
        implementation,dependency=fingerprints()
        if mpmath.__version__!="1.3.0" or mpmath.libmp.BACKEND!="python" or independence():
            raise Refused("unsupported backend version/import independence violation")
        if isinstance(source,(str,Path)):
            owned=open(source,"rb")
            stream=owned
        elif isinstance(source,bytes):
            stream=io.BytesIO(source)
        else:
            stream=source
        if materialize:
            # Bounded full replay convenience; streaming remains the default.
            payload=bytearray()
            while True:
                budget.check()
                part=stream.read(min(65536,limits.max_bytes+1-len(payload)))
                if not isinstance(part,bytes):
                    raise Invalid("binary witness stream required")
                if not part:
                    break
                payload.extend(part)
                if len(payload)>limits.max_bytes:
                    raise Refused("witness byte cap")
            stream=io.BytesIO(payload)
        reader=Reader(stream,limits)
        header=reader.header()
        if header.n_steps>limits.max_steps:
            raise Refused("step cap")
        model=Model()
        candidate=header.initial
        j=header.initial_j
        model.check(exact.relative(candidate),j,limits,budget,
                    exact.kinetic(candidate) if header.start_step==0 else None)
        current=candidate
        entered=exact.radius2(current)<400
        for _ in range(header.n_steps):
            budget.check()
            next_j,residual=reader.record()
            mid=exact.drift(current,j)
            model.check(exact.relative(mid),next_j,limits,budget)
            expected=exact.finish(mid,next_j)
            claimed=exact.state(tuple(v+d for v,d in zip(expected,residual)))
            if expected!=claimed:
                raise Invalid("executor state differs from independent exact transition")
            current,j=expected,next_j
            steps+=1
            entered |= exact.radius2(current)<400
        if current!=header.final:
            raise Invalid("executor final state differs bitwise")
        if reader.read(1,optional=True):
            raise Invalid("trailing witness bytes")
        if header.end=="R20_OUTBOUND" and not (entered and exact.outgoing(current)):
            raise Refused("requested R20 outbound exit not reached")
        budget.check()
        verdict,reason=Verdict.VALID,"all declared steps and raw state equality verified"
    except Invalid as e:
        verdict,reason=Verdict.INVALID,str(e)
    except (Refused,OSError,MemoryError) as e:
        verdict,reason=Verdict.REFUSED,str(e)
    finally:
        if owned is not None:
            owned.close()
    return Result(verdict,reason,steps,current,budget.evaluations,budget.max_precision,
                  time.process_time()-cpu,time.perf_counter()-start,
                  reader.count if reader else 0,reader.digest.hexdigest() if reader else "",
                  spec.SPEC_FINGERPRINT,implementation,dependency)
