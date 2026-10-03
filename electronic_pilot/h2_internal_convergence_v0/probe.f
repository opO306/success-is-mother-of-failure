      PROGRAM snapshot_probe
      USE MPMODULE
      IMPLICIT NONE
      TYPE(mp_real) x,one,two
      one='1'
      two='2'
      OPEN(81,FILE='probe.bin',STATUS='NEW',ACCESS='STREAM',
     > FORM='UNFORMATTED')
      x='0'
      CALL audit_word(81,x)
      x='-1.5'
      CALL audit_word(81,x)
      x=one+two**(-100)
      CALL audit_word(81,x)
      x=-(two**100)
      CALL audit_word(81,x)
      x=two**(-300)
      CALL audit_word(81,x)
      x='3.125'
      x=mpreal(x,5)
      CALL audit_word(81,x)
      CLOSE(81)
      END
