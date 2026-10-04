"""Only add clocks and export-only native enumeration to new source copies."""
from electronic_pilot.h2_internal_convergence_v0.instrument import (
    instrument as original_instrument, helper_bytes, strip_observer, SOURCE_SHA256)
import hashlib

BEGIN=b'c R04_OBSERVER_BEGIN\n'
END=b'c R04_OBSERVER_END\n'

def block(text):
    return BEGIN+text.encode('ascii')+END

def strip(source):
    while BEGIN in source:
        a=source.index(BEGIN);b=source.index(END,a)+len(END)
        source=source[:a]+source[b:]
    return strip_observer(source)

def clocks(source):
    original=source
    source=original_instrument(source,helper_bytes())
    edits=[
        (b'      CALL CALCEN(P,EN)\n','CALCEN_START','before'),
        (b'      CALL CALCEN(P,EN)\n','CALCEN_END','after'),
        (b'         CALL P_G(fA,2*X,2*Y,2*U,2*W) \n','INTEGRAL_START','before'),
        (b'         CALL P_G(fA,2*X,2*Y,2*U,2*W) \n','INTEGRAL_END','after'),
        (b'      CALL HAMLNORM(P)\n','MATRIX_END','after'),
        (b'      CALL audit_snapshot(HH,DN,NELM,EN,EPSKOR,\n','SNAPSHOT_START','before'),
        (b'      CALL invsg(HH,DN,NELM,EN,WF,EPSKOR,0,ITMAX,WA,ierror)\n','INVSG_START','before'),
        (b'      CALL audit_return(EN,WF,NELM,WA(1),ierror)\n','INVSG_END','after')]
    for anchor,tag,mode in edits:
        if source.count(anchor)!=1:raise ValueError('ambiguous clock anchor')
        call=block("      CALL r04_clock('"+tag+"')\n")
        source=source.replace(anchor,call+anchor if mode=='before' else anchor+call,1)
    source+=block("      SUBROUTINE r04_clock(tag)\n      IMPLICIT NONE\n"
                  "      CHARACTER*(*) tag\n      INTEGER*8 ticks,rate\n"
                  "      CALL SYSTEM_CLOCK(ticks,rate)\n"
                  "      OPEN(84,FILE='r04_clocks.log',STATUS='UNKNOWN',\n"
                  "     > POSITION='APPEND',FORM='FORMATTED')\n"
                  "      WRITE(84,*) tag,ticks,rate\n      CLOSE(84)\n      END\n")
    if strip(source)!=original:raise ValueError('observer changed calculation lines')
    return source

def enumeration(source):
    if hashlib.sha256(source).hexdigest()!=SOURCE_SHA256:raise ValueError('original source hash')
    anchor=b'      CALL CALCEN(P,EN)\n'
    code="      OPEN(83,FILE='basis.dat',STATUS='NEW')\n      WRITE(83,*) NELM\n"
    code+="      DO I=1,NELM\n         WRITE(83,*) DT(I,1:5)\n      ENDDO\n      CLOSE(83)\n      STOP\n"
    if source.count(anchor)!=1:raise ValueError('enumeration anchor')
    result=source.replace(anchor,block(code)+anchor,1)
    if strip(result)!=source:raise ValueError('enumeration copy changed source')
    return result
