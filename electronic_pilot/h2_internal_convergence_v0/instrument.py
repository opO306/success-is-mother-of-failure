"""Add observation blocks, retaining every original calculation line byte-for-byte."""
import hashlib
from pathlib import Path

SOURCE_SHA256 = "aa109cbd47cf5dcd2db57ce3da67bdaf69e22dfd9023e1219328e21413703d2d"
BEGIN = b"c AUDIT_V0_BEGIN\n"
END = b"c AUDIT_V0_END\n"


def block(text):
    return BEGIN + text.encode("ascii") + END


def strip_observer(source):
    while BEGIN in source:
        start = source.index(BEGIN)
        stop = source.index(END, start) + len(END)
        source = source[:start] + source[stop:]
    return source


def instrument(source, helper):
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA256
    edits = [
        (b"      CALL invsg(HH,DN,NELM,EN,WF,EPSKOR,0,ITMAX,WA,ierror)\n",
         "      CALL audit_snapshot(HH,DN,NELM,EN,EPSKOR,\n"
         "     > OMEGA,NMAX,NDIGITS,ITMAX)\n", "before"),
        (b"      CALL invsg(HH,DN,NELM,EN,WF,EPSKOR,0,ITMAX,WA,ierror)\n",
         "      CALL audit_return(EN,WF,NELM,WA(1),ierror)\n", "after"),
        (b"      errest = max(sixtn*n*reps,abs(eps))\n",
         "      CALL audit_begin(n,eig,eps,ijob,maxit,errest)\n", "after"),
        (b"         call leq1s(a,n,v,1,n,1,wa(ndet),ier)\n",
         "         CALL audit_leq(1,0,ier,wa(ndet+n))\n", "after"),
        (b"         call leq1s(a,n,v,1,n,2,wa(ndet),ier)\n",
         "         CALL audit_leq(2,it,ier,wa(ndet+n))\n", "after"),
        (b"         eig = eold+one/sm\n",
         "         CALL audit_step(it,eprev,eig,errest)\n", "after"),
        (b"      end do\n!\n!                         normalize eigenvector\n",
         "      CALL audit_exhausted(maxit)\n", "between"),
        (b"      wa(1) = wa(ndet+n)\n",
         "      CALL audit_normalized(ier)\n", "after"),
    ]
    result = source
    for anchor, observation, mode in edits:
        assert result.count(anchor) == 1, anchor
        if mode == "before":
            replacement = block(observation) + anchor
        elif mode == "after":
            replacement = anchor + block(observation)
        else:
            first, rest = anchor.split(b"\n", 1)
            replacement = first + b"\n" + block(observation) + rest
        result = result.replace(anchor, replacement, 1)
    result += block(helper.decode("ascii"))
    assert strip_observer(result) == source
    return result


def low_itmax(source):
    anchor = b"      integer, parameter :: itmax = 40 ! maximum number of inverse iterations"
    assert source.count(anchor) == 1
    return source.replace(anchor, anchor.replace(b"40", b"1"), 1)


def bad_en(source):
    lines = source.splitlines(keepends=True)
    assert len(lines) == 15 and b"energy EN" in lines[10]
    old = lines[10].split(None, 1)[0]
    lines[10] = lines[10].replace(old, b"-2.0", 1)
    return b"".join(lines)


def helper_bytes():
    return Path(__file__).with_name("observer.f").read_bytes()
