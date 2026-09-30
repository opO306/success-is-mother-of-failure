"""Bounded canonical wire format; full raw claims survive lossless compression."""
from dataclasses import dataclass
import hashlib
import json
import re
import struct
from . import exact, spec
from .types import Invalid, Refused

MAGIC=b"C1BRPV1\n"
HEADER_CAP=16384

@dataclass(frozen=True)
class Header:
    initial: tuple
    initial_j: tuple
    final: tuple
    n_steps: int
    start_step: int = 0
    end: str = "SEGMENT"

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf-8")

def varint(value):
    if type(value) is not int:
        raise Invalid("varint must be integer")
    value=2*value if value>=0 else -2*value-1
    out=bytearray()
    while value>=128:
        out.append((value&127)|128)
        value>>=7
    out.append(value)
    if len(out)>14:
        raise Invalid("oversized varint")
    return bytes(out)

class Reader:
    def __init__(self,stream,limits):
        self.stream,self.limits=stream,limits
        self.count=0
        self.digest=hashlib.sha256()

    def read(self,n,optional=False):
        if n>self.limits.max_bytes-self.count:
            if optional and n==1 and self.count==self.limits.max_bytes:
                probe=self.stream.read(1)
                if probe==b"":
                    return b""
            raise Refused("witness byte cap")
        pieces=[]
        left=n
        while left:
            part=self.stream.read(left)
            if not isinstance(part,bytes) or len(part)>left:
                raise Invalid("binary witness stream required")
            if not part:
                if optional and left==n:
                    return b""
                raise Refused("incomplete witness")
            self.count+=len(part)
            self.digest.update(part)
            pieces.append(part)
            left-=len(part)
        return b"".join(pieces)

    def integer(self):
        data=bytearray()
        value=0
        for i in range(14):
            byte=self.read(1)[0]
            data.append(byte)
            value|=(byte&127)<<(7*i)
            if not byte&128:
                signed=-(value//2)-1 if value&1 else value//2
                if bytes(data)!=varint(signed):
                    raise Invalid("noncanonical varint")
                return signed
        raise Invalid("oversized varint")

    def header(self):
        if self.read(len(MAGIC))!=MAGIC:
            raise Invalid("witness magic")
        size=struct.unpack("<I",self.read(4))[0]
        if size>HEADER_CAP:
            raise Invalid("header length cap")
        encoded=self.read(size)
        def pairs(entries):
            out={}
            for k,v in entries:
                if k in out:
                    raise Invalid("duplicate JSON key")
                out[k]=v
            return out
        try:
            value=json.loads(encoded,object_pairs_hook=pairs)
        except (ValueError,UnicodeError,RecursionError) as e:
            raise Invalid("malformed header JSON") from e
        fields={"schema","spec","initial","initial_j","final","n_steps","start_step","end"}
        if type(value) is not dict or set(value)!=fields or canonical(value)!=encoded:
            raise Invalid("noncanonical header/fields")
        if value["schema"]!="c1b1-replay-v1" or value["spec"]!=spec.SPEC_FINGERPRINT:
            raise Refused("unsupported schema/spec fingerprint")
        for field in ("n_steps","start_step"):
            if type(value[field]) is not int or not 0<=value[field]<=(1<<63)-1:
                raise Invalid("invalid step number")
        if value["n_steps"]<1:
            raise Invalid("nonempty interval required")
        if value["end"] not in ("SEGMENT","R20_OUTBOUND"):
            raise Refused("unsupported end contract")
        def values(field,count):
            items=value[field]
            if type(items) is not list or len(items)!=count:
                raise Invalid("header raw shape")
            out=[]
            for item in items:
                if type(item) is not str or len(item)>30 or not re.fullmatch(r"0|-?[1-9][0-9]*",item):
                    raise Invalid("noncanonical raw integer")
                out.append(exact.raw(int(item)))
            return tuple(out)
        return Header(values("initial",12),values("initial_j",3),values("final",12),
                      value["n_steps"],value["start_step"],value["end"])

    def record(self):
        j=exact.impulse(tuple(self.integer() for _ in range(3)))
        tag=self.read(1)[0]
        if tag==0:
            return j,(0,)*12
        if tag!=1:
            raise Invalid("unknown residual tag")
        residual=tuple(self.integer() for _ in range(12))
        if not any(residual) or any(abs(x)>spec.HIGH-spec.LOW for x in residual):
            raise Invalid("noncanonical/oversized state residual")
        return j,residual

def write(stream,header,records):
    """records yields (next J, executor's actual next 12-raw state). No verification grade."""
    value={"schema":"c1b1-replay-v1","spec":spec.SPEC_FINGERPRINT,
           "initial":[str(v) for v in exact.state(header.initial)],
           "initial_j":[str(v) for v in exact.impulse(header.initial_j)],
           "final":[str(v) for v in exact.state(header.final)],
           "n_steps":header.n_steps,"start_step":header.start_step,"end":header.end}
    encoded=canonical(value)
    if len(encoded)>HEADER_CAP:
        raise Invalid("header length cap")
    stream.write(MAGIC+struct.pack("<I",len(encoded))+encoded)
    previous,j=header.initial,header.initial_j
    count=0
    for next_j,claimed in records:
        next_j,claimed=exact.impulse(next_j),exact.state(claimed)
        candidate=exact.transition(previous,j,next_j)
        residual=tuple(b-a for a,b in zip(candidate,claimed))
        stream.write(b"".join(varint(v) for v in next_j))
        stream.write(b"\x01" if any(residual) else b"\x00")
        if any(residual):
            stream.write(b"".join(varint(v) for v in residual))
        previous,j=claimed,next_j
        count+=1
    if count!=header.n_steps or previous!=header.final:
        raise Invalid("producer record count/final mismatch")
