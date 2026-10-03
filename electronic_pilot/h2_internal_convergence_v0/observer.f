c Observation only. Original numerical variables are never assigned here.
      SUBROUTINE audit_word(iu,x)
      USE MPMODULE
      IMPLICIT NONE
      INTEGER iu,nl
      TYPE(mp_real) x
      INTEGER*8 words(mpwds+3)
      words=0
      words(1:3)=x%mpr(1:3)
      nl=int((x%mpr(1)+63)/64)
      if(nl.lt.1.or.nl.gt.mpwds) stop 'AUDIT invalid precision'
      if(x%mpr(3).ne.mpzero) words(4:3+nl)=x%mpr(5:4+nl)
      WRITE(iu) words
      END

      SUBROUTINE audit_value(tag,x)
      USE MPMODULE
      IMPLICIT NONE
      CHARACTER*(*) tag
      TYPE(mp_real) x
      INTEGER nl
      INTEGER*8 words(mpwds+3)
      words=0
      words(1:3)=x%mpr(1:3)
      nl=int((x%mpr(1)+63)/64)
      if(nl.lt.1.or.nl.gt.mpwds) stop 'AUDIT invalid precision'
      if(x%mpr(3).ne.mpzero) words(4:3+nl)=x%mpr(5:4+nl)
      WRITE(80,*) 'VALUE ',tag,words
      END

      SUBROUTINE audit_snapshot(h,s,n,e,eps,omega,nmax,nd,maxit)
      USE MPMODULE
      IMPLICIT NONE
      INTEGER n,omega,nmax,nd,maxit,i,ln
      TYPE(mp_real) h(*),s(*),e,eps
      INTEGER*8 header(9)
      ln=n*(n+1)/2
      OPEN(80,FILE='audit_invsg.log',STATUS='NEW',FORM='FORMATTED')
      WRITE(80,*) 'SNAPSHOT',n,omega,nmax,nd,maxit
      CALL audit_value('initial_EN',e)
      CALL audit_value('EPSKOR',eps)
      OPEN(81,FILE='audit_HS.bin',STATUS='NEW',ACCESS='STREAM',
     > FORM='UNFORMATTED')
      header=[int(z'4832534155445630',8),1_8,int(n,8),int(ln,8),
     > int(mpwds,8),int(nd,8),int(nmax,8),int(omega,8),int(maxit,8)]
      WRITE(81) header
      DO i=1,ln
         CALL audit_word(81,h(i))
      ENDDO
      DO i=1,ln
         CALL audit_word(81,s(i))
      ENDDO
      CLOSE(81)
      END

      SUBROUTINE audit_begin(n,e,eps,ijob,maxit,errest)
      USE MPMODULE
      IMPLICIT NONE
      INTEGER n,ijob,maxit,audit_count,audit_exhausted_flag
      COMMON /audit_state/ audit_count,audit_exhausted_flag
      TYPE(mp_real) e,eps,errest
      audit_count=0
      audit_exhausted_flag=0
      WRITE(80,*) 'BEGIN',n,maxit,ijob
      CALL audit_value('errest',errest)
      END

      SUBROUTINE audit_leq(job,it,ier,inertia)
      USE MPMODULE
      IMPLICIT NONE
      INTEGER job,it,ier,audit_count,audit_exhausted_flag
      COMMON /audit_state/ audit_count,audit_exhausted_flag
      TYPE(mp_real) inertia
      if(job.eq.2) audit_count=it
      WRITE(80,*) 'LEQ',job,it,ier
      if(job.eq.1.and.ier.eq.0) THEN
         CALL audit_value('factor_negative_count',inertia)
      ENDIF
      END

      SUBROUTINE audit_step(it,previous,updated,errest)
      USE MPMODULE
      IMPLICIT NONE
      INTEGER it
      TYPE(mp_real) previous,updated,errest,delta,abdelta,threshold
      delta=updated-previous
      abdelta=abs(delta)
      threshold=errest*abs(updated)
      WRITE(80,*) 'ITER',it
      CALL audit_value('previous',previous)
      CALL audit_value('updated',updated)
      CALL audit_value('signed_delta',delta)
      CALL audit_value('abs_delta',abdelta)
      CALL audit_value('threshold',threshold)
      END

      SUBROUTINE audit_exhausted(maxit)
      IMPLICIT NONE
      INTEGER maxit,audit_count,audit_exhausted_flag
      COMMON /audit_state/ audit_count,audit_exhausted_flag
      audit_exhausted_flag=1
      WRITE(80,*) 'EXHAUSTED',maxit
      END

      SUBROUTINE audit_normalized(ier)
      IMPLICIT NONE
      INTEGER ier,audit_count,audit_exhausted_flag
      COMMON /audit_state/ audit_count,audit_exhausted_flag
      if(audit_exhausted_flag.eq.1) THEN
         WRITE(80,*) 'NORMALIZED_EXHAUSTED',audit_count,ier
      ELSE
         WRITE(80,*) 'NORMALIZED_CONVERGED',audit_count,ier
      ENDIF
      END

      SUBROUTINE audit_return(e,v,n,inertia,ierror)
      USE MPMODULE
      IMPLICIT NONE
      INTEGER n,i,ierror
      TYPE(mp_real) e,v(*),inertia
      INTEGER*8 header(4)
      WRITE(80,*) 'RETURN',ierror
      CALL audit_value('final_EN',e)
      if(ierror.eq.0) CALL audit_value('wa1',inertia)
      CLOSE(80)
      OPEN(82,FILE='audit_EV.bin',STATUS='NEW',ACCESS='STREAM',
     > FORM='UNFORMATTED')
      header=[int(z'4832564155445630',8),1_8,int(n,8),int(mpwds,8)]
      WRITE(82) header
      CALL audit_word(82,e)
      DO i=1,n
         CALL audit_word(82,v(i))
      ENDDO
      CLOSE(82)
      END
