"""Same read contract on original A transport and existing guardian CLI; no mutations."""
from pathlib import Path
import subprocess,time
from read_retry import read_retry,TemporaryReadFailure,transient_stderr

def transport_class(original,absolute_deadline,outer_check):
    class ReadTransport(original.Transport):
        def show(self,name,timeout=12):
            deadline=min(absolute_deadline,getattr(self,'_read_phase_deadline',float('inf')))
            if self.start_ns is not None:deadline=min(deadline,self.start_ns/1e9+600)
            def check():
                outer_check()
                if name=='phase_control':self.stop_control_check()
                if self.start_ns is not None:self.age()
            def perform(left):
                try:return super(ReadTransport,self).show(name,timeout=left)
                except RuntimeError as error:
                    if str(error)!='ADMIN_PHASE_FAILED:'+name:raise
                    prefix=self.out/('%03d_'%self.index+name)
                    if not transient_stderr(prefix.with_suffix('.stderr').read_bytes()):raise
                    raise TemporaryReadFailure(str(error)) from error
            return read_retry(perform,('show','instance',self.auth['instance_id']),timeout=timeout,absolute_deadline=deadline,check=check)
        def control(self,required_seconds,*,phase_deadline=None):
            prior=getattr(self,'_read_phase_deadline',float('inf'))
            self._read_phase_deadline=min(prior,absolute_deadline,phase_deadline if phase_deadline is not None else float('inf'))
            try:return super().control(required_seconds,phase_deadline=phase_deadline)
            finally:self._read_phase_deadline=prior
    return ReadTransport

def checked_class(original,absolute_deadline,log=None):
    class ReadChecked(original.CheckedCli):
        def show(self):
            # Keep original 12s initial/STOP caller allowance, sharing one deadline.
            def perform(left):
                try:result=subprocess.run([self.path,'--raw','--retry','1','show','instance',self.instance],capture_output=True,timeout=left)
                except subprocess.TimeoutExpired as error:
                    if log:log(dict(event='READ_TIMEOUT',instance=self.instance,timeout_seconds=left,error=repr(error)))
                    raise
                if log:log(dict(event='READ_REPLY',instance=self.instance,returncode=result.returncode,stdout_b64=__import__('base64').b64encode(result.stdout).decode(),stderr_b64=__import__('base64').b64encode(result.stderr).decode()))
                if result.returncode:
                    if transient_stderr(result.stderr):raise TemporaryReadFailure('PRESERVED_TRANSIENT_READ')
                    raise OSError('CONTROL_CLI_FAILURE')
                record=original.decode(result.stdout);state=original.inspect(record,self.approval,self.role)
                if state['state']=='STARTING':raise ValueError('EXITED_WITH_RUNNING_INTENT_IS_NOT_STOPPED')
                self.role='guardian_observe'
                return record
            return read_retry(perform,('show','instance',self.instance),timeout=self.timeout_seconds,absolute_deadline=absolute_deadline,check=lambda:None)
        # stop/call remain the original guarded mutation paths without a retry wrapper.
    return ReadChecked
